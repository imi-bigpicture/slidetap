#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Service for accessing image data."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from time import monotonic
from types import TracebackType
from typing import TypeVar
from uuid import UUID

from wsidicom import WsiDicom
from wsidicom.errors import WsiDicomNotFoundError
from wsidicomizer import WsiDicomizer

from slidetap.config import ImageCacheConfig
from slidetap.external_interfaces.image_view import ImageViewInterface
from slidetap.model import Dzi, ImageFormat, ImageToView
from slidetap.services.database_service import DatabaseService

Viewed = TypeVar("Viewed")

MISSING_FILES = (FileNotFoundError, WsiDicomNotFoundError)
"""What reading an image raises where its files are not there."""


@dataclass
class ImageCacheItem:
    """A opened image (WsiDicom) that is cached."""

    item: WsiDicom
    last_accessed: datetime = field(default_factory=datetime.now)
    users: int = 0
    """Number of requests currently reading the image."""

    def close(self):
        self.item.close()


CacheKey = tuple[UUID, str]
"""An image by its uid and the folder it was opened from."""


class ImageCache:
    """A collection of cached images.

    Safe to use from several threads. An image is only closed and removed when
    the cache is over its size and no request is reading the image.

    An image is cached by the folder it was opened from too, so that one moved,
    as a converted image is from its download, is opened again where it now is.
    What was opened from where it was is closed once no request reads it.
    """

    def __init__(self, config: ImageCacheConfig):
        self._cache: dict[CacheKey, ImageCacheItem] = {}
        self._cache_size = config.cache_size
        self._lock = Lock()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self):
        with self._lock:
            for item in self._cache.values():
                item.close()
            self._cache.clear()

    @property
    def is_full(self) -> bool:
        return len(self._cache) > self._cache_size

    @contextmanager
    def get(self, image: ImageToView) -> Generator[WsiDicom | None, None, None]:
        """The opened image, or None if the image has no files to open.

        The image is kept open for as long as the context is entered.
        """
        if image.folder_path is None:
            yield None
            return
        cached_item = self._acquire(image, (image.uid, str(image.folder_path)))
        if cached_item is None:
            yield None
            return
        try:
            yield cached_item.item
        finally:
            with self._lock:
                cached_item.users -= 1
                self._remove_old()

    def _acquire(self, image: ImageToView, key: CacheKey) -> ImageCacheItem | None:
        with self._lock:
            self._remove_moved(key)
            cached_item = self._cache.get(key)
            if cached_item is not None:
                cached_item.last_accessed = datetime.now()
                cached_item.users += 1
                return cached_item
        # Opened outside the lock, as opening can be slow. Should another request
        # have opened the same image meanwhile, the image already cached is used.
        opened_item = self._open(image)
        if opened_item is None:
            return None
        with self._lock:
            cached_item = self._cache.get(key)
            if cached_item is None:
                cached_item = opened_item
                self._cache[key] = cached_item
            else:
                opened_item.close()
            cached_item.last_accessed = datetime.now()
            cached_item.users += 1
            self._remove_old()
        return cached_item

    def _open(self, image: ImageToView) -> ImageCacheItem | None:
        if image.folder_path is None:
            return None
        if image.format == ImageFormat.DICOM_WSI:
            wsi = WsiDicom.open(image.folder_path)
        elif image.format == ImageFormat.OTHER_WSI and image.filenames:
            wsi = WsiDicomizer.open(
                Path(image.folder_path).joinpath(image.filenames[0])
            )
        else:
            return None
        return ImageCacheItem(wsi)

    def _remove_moved(self, key: CacheKey):
        """Close and remove the image as it was opened from another folder,
        where no request is reading it. Called holding the lock."""
        uid, _ = key
        for moved_key in [
            cached_key
            for cached_key, cached_item in self._cache.items()
            if cached_key[0] == uid and cached_key != key and cached_item.users == 0
        ]:
            self._cache.pop(moved_key).close()

    def _remove_old(self):
        """Close and remove the least recently used images that no request is
        reading, until the cache is within its size. Called holding the lock."""
        while self.is_full and self._remove_oldest_not_in_use():
            pass

    def _remove_oldest_not_in_use(self) -> bool:
        not_in_use = [
            (key, cached_item)
            for key, cached_item in self._cache.items()
            if cached_item.users == 0
        ]
        if not not_in_use:
            return False
        oldest_key, oldest_item = min(
            not_in_use, key=lambda entry: entry[1].last_accessed
        )
        del self._cache[oldest_key]
        oldest_item.close()
        return True


class ImageService:
    """Views the images, through the image view interface of the application.

    What is read of an image to view it is kept for a few seconds, see
    :py:attr:`ImageCacheConfig.image_seconds`, as a viewer asks for many tiles
    at once and each would otherwise read it again. An image whose files are
    not where it was kept as being, as one moved meanwhile, is read again and
    viewed where it now is. One whose files are gone is not found.
    """

    def __init__(
        self,
        database_service: DatabaseService,
        image_view_interface: ImageViewInterface,
        config: ImageCacheConfig,
    ):
        self._database_service = database_service
        self._image_view_interface = image_view_interface
        self._image_seconds = config.image_seconds
        self._images: dict[UUID, tuple[float, ImageToView]] = {}
        self._images_lock = Lock()

    def get_thumbnail(
        self, image_uid: UUID, width: int, height: int, format: str
    ) -> bytes | None:
        """A thumbnail of the image at the given size, or None if there is no
        such image or it has none to give."""
        try:
            return self._view(
                image_uid,
                lambda image: self._image_view_interface.get_thumbnail(
                    image, width, height, format
                ),
            )
        except ValueError:
            return None

    def get_dzi(self, image_uid: UUID, base_url: str) -> Dzi:
        """The Deep Zoom description of the image.

        Raises
        ------
        ValueError
            If there is no such image, or it cannot be read.
        """
        return self._view(
            image_uid,
            lambda image: self._image_view_interface.get_dzi(image, base_url),
        )

    def get_tile(
        self,
        image_uid: UUID,
        dzi_level: int,
        x: int,
        y: int,
        extension: str,
        z: int | None = None,
    ) -> bytes:
        """A tile of the image.

        Raises
        ------
        ValueError
            If there is no such image, or it cannot be read.
        """
        return self._view(
            image_uid,
            lambda image: self._image_view_interface.get_tile(
                image, dzi_level, x, y, extension, z
            ),
        )

    def _view(self, image_uid: UUID, view: Callable[[ImageToView], Viewed]) -> Viewed:
        """View the image as it was read within the last seconds, and, where
        its files are not there, as it is read now: once, and only where it has
        moved since."""
        image = self._existing_image(image_uid)
        try:
            return view(image)
        except MISSING_FILES as exception:
            with self._images_lock:
                self._images.pop(image_uid, None)
            now = self._image(image_uid)
            if now is None:
                raise ValueError(f"Image with UID {image_uid} not found.") from (
                    exception
                )
            if now.folder_path == image.folder_path:
                raise ValueError(
                    f"The files of image {image_uid} are not there."
                ) from exception
        try:
            return view(now)
        except MISSING_FILES as exception:
            raise ValueError(
                f"The files of image {image_uid} are not there."
            ) from exception

    def _image(self, image_uid: UUID) -> ImageToView | None:
        """The image as read within the last seconds, or as read now. An image
        not there is not kept, so that one added is viewed at once."""
        now = monotonic()
        with self._images_lock:
            kept = self._images.get(image_uid)
            if kept is not None and now - kept[0] < self._image_seconds:
                return kept[1]
        with self._database_service.get_session(commit=False) as session:
            image = self._database_service.get_image_to_view(session, image_uid)
        with self._images_lock:
            # What has passed its time is dropped, so that what is kept is
            # only what was viewed within the last seconds.
            for uid in [
                uid
                for uid, (read_at, _) in self._images.items()
                if now - read_at >= self._image_seconds
            ]:
                del self._images[uid]
            if image is not None and self._image_seconds > 0:
                self._images[image_uid] = (now, image)
        return image

    def _existing_image(self, image_uid: UUID) -> ImageToView:
        image = self._image(image_uid)
        if image is None:
            raise ValueError(f"Image with UID {image_uid} not found.")
        return image
