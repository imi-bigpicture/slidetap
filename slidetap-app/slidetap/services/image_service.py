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
from typing import Annotated, Dict, Generator, Iterable, Optional, Type
from uuid import UUID

from sqlalchemy import select
from wsidicom import WsiDicom
from wsidicomizer import WsiDicomizer

from slidetap.config import Config
from slidetap.database import DatabaseImage
from slidetap.model import Dzi, Image
from slidetap.services.database_service import DatabaseService
from slidetap.services.storage_service import StorageService


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

    def __init__(self, config: Config, database_service: DatabaseService):
        self._database_service = database_service
        self._cache: Dict[UUID, ImageCacheItem] = {}
        self._cache_size = config.image_cache_config.cache_size

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
    def get(self, uid: UUID) -> Generator[Optional[WsiDicom], None, None]:
        cached_item = self._aquire(uid)
        if cached_item is None:
            return None
        holds_lock = cached_item.in_use.acquire(blocking=False)
        try:
            yield cached_item.item
        finally:
            if holds_lock:
                cached_item.in_use.release()
                self._remove_old()

    def _aquire(self, uid: UUID) -> Optional[ImageCacheItem]:
        if uid in self._cache:
            cached_item = self._cache[uid]
            cached_item.last_accessed = datetime.now()
        else:
            cached_item = self._open(uid)
            if cached_item is None:
                return None
            self._insert_into_cache(uid, cached_item)
        return cached_item

    def _open(self, uid: UUID) -> Optional[ImageCacheItem]:
        with self._database_service.get_session() as session:
            image = self._database_service.get_image(session, uid)
            if image.post_processed and image.folder_path is not None:
                wsi = WsiDicom.open(image.folder_path)
            elif image.folder_path is not None and len(image.files) > 0:
                wsi = WsiDicomizer.open(
                    Path(image.folder_path).joinpath(image.files[0].filename)
                )
            else:
                return None
            return ImageCacheItem(wsi)

    def _insert_into_cache(self, uid: UUID, item: ImageCacheItem):
        self._remove_old()
        self._cache[uid] = item

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
    def __init__(
        self,
        storage_service: StorageService,
        database_service: DatabaseService,
        image_cache: ImageCache,
    ):
        # if image_cache is None:
        #     image_cache = ImageCache(3)
        self._storage_service = storage_service
        self._database_service = database_service
        self._image_cache = image_cache

    # def __enter__(self):
    #     return self

    # def __exit__(
    #     self,
    #     exc_type: Optional[Type[BaseException]],
    #     exc_val: Optional[BaseException],
    #     exc_tb: Optional[TracebackType],
    # ) -> None:
    #     self.close()

    # def close(self):
    #     self._image_cache.close()

    def get_images_with_thumbnail(
        self, dataset_uid: UUID, batch_uid: Optional[UUID] = None
    ) -> Iterable[Image]:
        query = select(DatabaseImage).filter(
            DatabaseImage.dataset_uid == dataset_uid,
            DatabaseImage.thumbnail_path.isnot(None),
        )
        if batch_uid is not None:
            query = query.filter(DatabaseImage.batch_uid == batch_uid)
        with self._database_service.get_session() as session:
            images = session.scalars(query)
            return [image.model for image in images]

    def get_thumbnail(
        self, image_uid: UUID, width: int, height: int, format: str
    ) -> Optional[bytes]:
        with self._database_service.get_session() as session:
            image = self._database_service.get_optional_image(session, image_uid)
            if image is None or image.folder_path is None:
                return None
            if image.thumbnail_path is None:
                thumbnail = self._create_thumbnail(image, width, height, format)
                if image.batch is not None:
                    self._storage_service.store_thumbnail(
                        image.batch.project.model, image.model, thumbnail
                    )
                return thumbnail

            return self._storage_service.get_thumbnail(image.model, (width, height))

    def get_dzi(self, image_uid: UUID, base_url: str) -> Dzi:
        with self._image_cache.get(image_uid) as wsi:
            if wsi is None:
                raise ValueError(f"Image with UID {image_uid} not found in cache.")
            return Dzi(
                url=base_url,
                width=wsi.size.width,
                height=wsi.size.height,
                tile_size=wsi.tile_size.width,
                tile_format="jpeg",
                planes=wsi.pyramids[0].base_level.focal_planes,
                channels=wsi.pyramids[0].base_level.optical_paths,
            )

    def get_tile(
        self,
        image_uid: UUID,
        dzi_level: int,
        x: int,
        y: int,
        extension: str,
        z: Optional[int] = None,
    ) -> bytes:
        with self._image_cache.get(image_uid) as wsi:
            if wsi is None:
                raise ValueError(f"Image with UID {image_uid} not found in cache.")
            level = wsi.pyramids[0].highest_level - dzi_level
            return wsi.read_encoded_tile(level, (x, y), z)

    def _create_thumbnail(
        self, image: DatabaseImage, width: int, height: int, format: str
    ):
        if image.folder_path is None:
            raise ValueError("No image files found.")
        if image.post_processed:
            with WsiDicom.open(image.folder_path) as wsi:
                thumbnail = wsi.read_thumbnail((width, height))

        else:
            with WsiDicomizer.open(
                Path(image.folder_path).joinpath(image.files[0].filename)
            ) as wsi:
                thumbnail = wsi.read_thumbnail((width, height))
        with io.BytesIO() as output:
            thumbnail.save(output, format)
            return output.getvalue()
