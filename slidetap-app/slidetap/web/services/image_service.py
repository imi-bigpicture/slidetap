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

import io
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Semaphore
from types import TracebackType
from typing import Dict, Generator, Iterable, Optional, Type
from uuid import UUID

from slidetap.database import Image, Project
from slidetap.storage import Storage
from slidetap.web.model import Dzi
from wsidicom import WsiDicom
from wsidicomizer import WsiDicomizer


@dataclass
class ImageCacheItem:
    """A opened image (WsiDicom) that is cached."""

    item: WsiDicom
    last_accessed: datetime = datetime.now()
    in_use: Semaphore = Semaphore()

    def close(self):
        self.item.close()


class ImageCache:
    """A collection of cached images."""

    def __init__(self, cache_size: int):
        self._cache: Dict[Path, ImageCacheItem] = {}
        self._cache_size = cache_size

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self):
        for item in self._cache.values():
            item.close()

    @property
    def is_full(self) -> bool:
        return len(self._cache) > self._cache_size

    @contextmanager
    def get(self, path: Path) -> Generator[WsiDicom, None, None]:
        cached_item = self._aquire(path)
        holds_lock = cached_item.in_use.acquire(blocking=False)
        try:
            yield cached_item.item
        finally:
            if holds_lock:
                cached_item.in_use.release()
                self._remove_old()

    def _aquire(self, path: Path) -> ImageCacheItem:
        if path in self._cache:
            cached_item = self._cache[path]
            cached_item.last_accessed = datetime.now()
        else:
            cached_item = self._open(path)
            self._insert_into_cache(path, cached_item)
        return cached_item

    def _open(self, path: Path) -> ImageCacheItem:
        wsi = WsiDicom.open(path)
        return ImageCacheItem(wsi)

    def _insert_into_cache(self, path: Path, item: ImageCacheItem):
        self._remove_old()
        self._cache[path] = item

    def _remove_old(self):
        while self.is_full and self._remove_oldest_not_in_use():
            pass

    def _remove_oldest_not_in_use(self) -> bool:
        try:
            to_remove = next(
                path
                for (path, item) in sorted(
                    self._cache.items(), key=lambda item: item[1].last_accessed
                )
                if item.in_use.acquire(False)
            )
            removed_item = self._cache.pop(to_remove)
            removed_item.close()
        except StopIteration:
            return False
        return True


class ImageService:
    def __init__(self, storage: Storage, image_cache: Optional[ImageCache] = None):
        if image_cache is None:
            image_cache = ImageCache(3)
        self._storage = storage
        self._image_cache = image_cache

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self):
        self._image_cache.close()

    def get_images_with_thumbnail(self, project_uid: UUID) -> Optional[Iterable[Image]]:
        project = Project.get_optional(project_uid)
        if project is None:
            return None
        return Image.get_images_with_thumbnails(project)

    def get_thumbnail(
        self, image_uid: UUID, width: int, height: int, format: str
    ) -> Optional[bytes]:
        image = Image.get_optional(image_uid)
        if image is None:
            return None
        if image.thumbnail_path is None:
            file = next(file for file in image.files)
            with WsiDicomizer.open(
                Path(image.folder_path).joinpath(file.filename)
            ) as wsi:
                thumbnail = wsi.read_thumbnail((width, height))
                with io.BytesIO() as output:
                    thumbnail.save(output, format)
                    return output.getvalue()

        return self._storage.get_thumbnail(image, (width, height))

    def get_dzi(self, image_uid: UUID, base_url: str) -> Dzi:
        image = Image.get(image_uid)
        # with self._image_cache.get(Path(image.folder_path)) as wsi:
        if image.post_processed:
            with WsiDicom.open(Path(image.folder_path)) as wsi:
                return Dzi(
                    base_url,
                    wsi.size.width,
                    wsi.size.height,
                    wsi.tile_size.width,
                    "jpeg",
                    wsi.pyramids[0].base_level.focal_planes,
                    wsi.pyramids[0].base_level.optical_paths,
                )
        elif len(image.files) > 0:
            with WsiDicomizer.open(
                Path(image.folder_path).joinpath(image.files[0].filename)
            ) as wsi:
                return Dzi(
                    base_url,
                    wsi.size.width,
                    wsi.size.height,
                    wsi.tile_size.width,
                    "jpeg",
                    wsi.pyramids[0].base_level.focal_planes,
                    wsi.pyramids[0].base_level.optical_paths,
                )
        raise ValueError("No image files found.")

    def get_tile(
        self,
        image_uid: UUID,
        dzi_level: int,
        x: int,
        y: int,
        extension: str,
        z: Optional[int] = None,
    ) -> bytes:
        image = Image.get(image_uid)
        # with self._image_cache.get(Path(image.folder_path)) as wsi:
        with WsiDicom.open(Path(image.folder_path)) as wsi:
            level = wsi.pyramids[0].highest_level - dzi_level
            return wsi.read_encoded_tile(level, (x, y), z)
