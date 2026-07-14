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

"""Tests for the image status transitions of storing."""

from uuid import uuid4

import pytest

from slidetap.database import DatabaseImage
from slidetap.database.attribute import NotAllowedActionError
from slidetap.model import ImageFormat, ImageStatus


@pytest.fixture()
def image() -> DatabaseImage:
    return DatabaseImage(
        dataset_uid=uuid4(),
        batch_uid=uuid4(),
        schema_uid=uuid4(),
        identifier="image identifier",
        format=ImageFormat.OTHER_WSI,
    )


@pytest.mark.unittest
class TestImageStatus:
    def test_storing_a_post_processed_image_stores_it(
        self, image: DatabaseImage
    ) -> None:
        """An image is claimed as storing, and stored once it has been."""
        # Arrange
        image.status = ImageStatus.POST_PROCESSED

        # Act
        image.set_as_storing()
        stored_from = image.status
        image.set_as_stored()

        # Assert
        assert stored_from == ImageStatus.STORING
        assert image.status == ImageStatus.STORED

    def test_storing_a_storing_image_is_allowed(self, image: DatabaseImage) -> None:
        """A store that is redelivered claims an image it is already storing.

        The store task selects images that are storing, so that images left
        storing by a failed attempt are stored again.
        """
        # Arrange
        image.status = ImageStatus.STORING

        # Act
        image.set_as_storing()

        # Assert
        assert image.status == ImageStatus.STORING

    def test_storing_a_stored_image_is_not_allowed(self, image: DatabaseImage) -> None:
        """An image that is stored is not stored again."""
        # Arrange
        image.status = ImageStatus.STORED

        # Act & Assert
        with pytest.raises(NotAllowedActionError):
            image.set_as_storing()

    def test_setting_a_post_processed_image_as_stored_is_not_allowed(
        self, image: DatabaseImage
    ) -> None:
        """An image is only stored from being stored, never straight from being
        post-processed, so that an image is never recorded as stored without a
        store having been attempted."""
        # Arrange
        image.status = ImageStatus.POST_PROCESSED

        # Act & Assert
        with pytest.raises(NotAllowedActionError):
            image.set_as_stored()

    def test_failing_to_store_a_storing_image_fails_it(
        self, image: DatabaseImage
    ) -> None:
        """An image that cannot be stored is set as storing failed."""
        # Arrange
        image.status = ImageStatus.STORING

        # Act
        image.set_as_storing_failed()

        # Assert
        assert image.status == ImageStatus.STORING_FAILED
        assert image.failed

    def test_retrying_a_storing_failed_image_resets_it_to_post_processed(
        self, image: DatabaseImage
    ) -> None:
        """A retried image is stored again, and is thus post-processed again.

        The store task selects images that are post-processed, so this is what
        makes the image be stored by the batch being stored again.
        """
        # Arrange
        image.status = ImageStatus.STORING_FAILED

        # Act
        image.reset_as_post_processed()

        # Assert
        assert image.status == ImageStatus.POST_PROCESSED

    def test_resetting_a_storing_image_as_post_processed_is_not_allowed(
        self, image: DatabaseImage
    ) -> None:
        """An image a worker may still be storing is not reset.

        A store left by a worker that died is recovered by the stalled job being
        retried, which stores the images it left storing again.
        """
        # Arrange
        image.status = ImageStatus.STORING

        # Act & Assert
        with pytest.raises(NotAllowedActionError):
            image.reset_as_post_processed()

    def test_stored_image_is_processed(self, image: DatabaseImage) -> None:
        """A stored image still holds processed image data.

        Storing moves the folder, but does not change what it holds, so readers
        that open the processed image do so for a stored image as well.
        """
        # Arrange
        image.status = ImageStatus.STORED

        # Act & Assert
        assert image.processed
