#    Copyright 2026 SECTRA AB
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

"""Tests for keeping opened images in the image cache."""

from uuid import UUID, uuid4

import pytest
from decoy import Decoy

from slidetap.config import ImageCacheConfig
from slidetap.services.database_service import DatabaseService
from slidetap.services.image_service import ImageCache, ImageCacheItem


class FakeImage:
    """Stands in for an opened WsiDicom, recording whether it was closed."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class OpeningImageCache(ImageCache):
    """Image cache that opens fake images instead of reading the database."""

    def __init__(self, cache_size: int, database_service: DatabaseService):
        super().__init__(ImageCacheConfig(cache_size=cache_size), database_service)
        self.opened: dict[UUID, FakeImage] = {}

    def _open(self, uid: UUID) -> ImageCacheItem | None:
        image = FakeImage()
        self.opened[uid] = image
        return ImageCacheItem(image)  # type: ignore[arg-type]


@pytest.fixture()
def database_service(decoy: Decoy) -> DatabaseService:
    return decoy.mock(cls=DatabaseService)


@pytest.mark.unittest
class TestImageCache:
    def test_items_do_not_share_state(self):
        # Arrange
        first = ImageCacheItem(FakeImage())  # type: ignore[arg-type]
        second = ImageCacheItem(FakeImage())  # type: ignore[arg-type]

        # Act
        first.users += 1

        # Assert
        assert second.users == 0

    def test_evicts_least_recently_used_image_repeatedly(
        self, database_service: DatabaseService
    ):
        # Arrange
        cache = OpeningImageCache(1, database_service)
        uids = [uuid4() for _ in range(4)]

        # Act
        for uid in uids:
            with cache.get(uid):
                pass

        # Assert
        assert len(cache._cache) == 1
        assert [cache.opened[uid].closed for uid in uids] == [True, True, True, False]

    def test_image_in_use_is_not_evicted(self, database_service: DatabaseService):
        # Arrange
        cache = OpeningImageCache(0, database_service)
        in_use_uid = uuid4()
        other_uid = uuid4()

        # Act
        with cache.get(in_use_uid):
            with cache.get(other_uid):
                pass
            in_use_closed_while_reading = cache.opened[in_use_uid].closed

        # Assert
        assert not in_use_closed_while_reading
        assert cache.opened[other_uid].closed
        assert cache.opened[in_use_uid].closed

    def test_image_without_files_gives_none(self, database_service: DatabaseService):
        # Arrange
        cache = ImageCache(ImageCacheConfig(cache_size=1), database_service)
        cache._open = lambda uid: None  # type: ignore[method-assign]

        # Act
        with cache.get(uuid4()) as image:
            result = image

        # Assert
        assert result is None
