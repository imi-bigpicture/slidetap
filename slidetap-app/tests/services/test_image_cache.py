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

from slidetap.config import ImageCacheConfig
from slidetap.model import ImageFormat, ImageStatus, ImageToView
from slidetap.services.image_service import ImageCache, ImageCacheItem


class FakeImage:
    """Stands in for an opened WsiDicom, recording whether it was closed."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class OpeningImageCache(ImageCache):
    """Image cache that opens fake images instead of reading files."""

    def __init__(self, cache_size: int):
        super().__init__(ImageCacheConfig(cache_size=cache_size))
        self.opened: dict[tuple[UUID, str | None], FakeImage] = {}

    def _open(self, image: ImageToView) -> ImageCacheItem | None:
        opened = FakeImage()
        self.opened[(image.uid, image.folder_path)] = opened
        return ImageCacheItem(opened)  # type: ignore[arg-type]


def _image(
    uid: UUID | None = None, folder_path: str | None = "/download"
) -> ImageToView:
    return ImageToView(
        uid=uid or uuid4(),
        status=ImageStatus.PRE_PROCESSED,
        format=ImageFormat.OTHER_WSI,
        folder_path=folder_path,
        filenames=("slide.svs",),
    )


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

    def test_evicts_least_recently_used_image_repeatedly(self):
        # Arrange
        cache = OpeningImageCache(1)
        images = [_image() for _ in range(4)]

        # Act
        for image in images:
            with cache.get(image):
                pass

        # Assert
        assert len(cache._cache) == 1
        assert [
            cache.opened[(image.uid, image.folder_path)].closed for image in images
        ] == [True, True, True, False]

    def test_image_in_use_is_not_evicted(self):
        # Arrange
        cache = OpeningImageCache(0)
        in_use = _image()
        other = _image()

        # Act
        with cache.get(in_use):
            with cache.get(other):
                pass
            in_use_closed_while_reading = cache.opened[
                (in_use.uid, in_use.folder_path)
            ].closed

        # Assert
        assert not in_use_closed_while_reading
        assert cache.opened[(other.uid, other.folder_path)].closed
        assert cache.opened[(in_use.uid, in_use.folder_path)].closed

    def test_a_moved_image_is_opened_where_it_now_is(self):
        # Arrange
        cache = OpeningImageCache(10)
        uid = uuid4()
        downloaded = _image(uid, "/download")
        converted = _image(uid, "/processing")
        with cache.get(downloaded):
            pass

        # Act
        with cache.get(converted) as opened:
            read = opened

        # Assert
        assert read is cache.opened[(uid, "/processing")]
        assert cache.opened[(uid, "/download")].closed
        assert list(cache._cache) == [(uid, "/processing")]

    def test_a_moved_image_being_read_is_closed_after(self):
        # Arrange
        cache = OpeningImageCache(10)
        uid = uuid4()
        downloaded = _image(uid, "/download")
        converted = _image(uid, "/processing")

        # Act
        with cache.get(downloaded):
            with cache.get(converted):
                pass
            closed_while_reading = cache.opened[(uid, "/download")].closed
        with cache.get(converted):
            pass

        # Assert
        assert not closed_while_reading
        assert cache.opened[(uid, "/download")].closed

    def test_image_without_files_gives_none(self):
        # Arrange
        cache = OpeningImageCache(1)

        # Act
        with cache.get(_image(folder_path=None)) as image:
            result = image

        # Assert
        assert result is None
        assert cache.opened == {}
