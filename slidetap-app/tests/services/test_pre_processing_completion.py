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

"""When a batch has finished pre-processing its images.

Asked of the database rather than of a mock, since what is being pinned is
which rows the query leaves out. An image that failed is left in the batch for
somebody to deal with, and the batch has to be able to finish around it: what
it is under is flagged when the batch finishes pre-processing, so a batch that
never finishes is a case nobody is ever asked to look at.
"""

from uuid import UUID, uuid4

import pytest

from slidetap.database import DatabaseImage
from slidetap.model import ImageFormat, ImageStatus
from slidetap.services import DatabaseService
from slidetap.task.tasks import PRE_PROCESSING_SETTLED


@pytest.fixture()
def batch_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def dataset_uid() -> UUID:
    return uuid4()


def _add_image(
    database_service: DatabaseService,
    batch_uid: UUID,
    dataset_uid: UUID,
    identifier: str,
    status: ImageStatus,
    selected: bool = True,
) -> UUID:
    with database_service.get_session() as session:
        image = DatabaseImage(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=uuid4(),
            identifier=identifier,
            format=ImageFormat.OTHER_WSI,
        )
        image.status = status
        image.selected = selected
        session.add(image)
        session.commit()
        return image.uid


def _unfinished_image(database_service: DatabaseService, batch_uid: UUID) -> str | None:
    """The image the pre-processing task finds still on its way, by identifier,
    or None where the batch is finished. Read inside the session, since what is
    asserted on is the answer rather than the row."""
    with database_service.get_session() as session:
        image = database_service.get_first_image_for_batch(
            session,
            batch_uid=batch_uid,
            exclude_status=PRE_PROCESSING_SETTLED,
            selected=True,
        )
        return image.identifier if image is not None else None


@pytest.mark.integration
class TestPreProcessingCompletion:
    def test_a_batch_finishes_around_an_image_that_failed_to_download(
        self,
        sqlite_database_service: DatabaseService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        """The failure this guards against: an image the source would not hand
        over holds the batch at pre-processing for good, and every case in it
        goes unflagged, since flagging is what finishing pre-processing does.
        """
        # Arrange
        _add_image(
            sqlite_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.PRE_PROCESSED,
        )
        _add_image(
            sqlite_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.DOWNLOADING_FAILED,
        )

        # Act
        unfinished = _unfinished_image(sqlite_database_service, batch_uid)

        # Assert
        assert unfinished is None

    def test_an_image_still_on_its_way_holds_the_batch(
        self,
        sqlite_database_service: DatabaseService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        """The other half of it: a batch is not finished while an image is
        still going to arrive."""
        # Arrange
        _add_image(
            sqlite_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.PRE_PROCESSED,
        )
        _add_image(
            sqlite_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.DOWNLOADING,
        )

        # Act
        unfinished = _unfinished_image(sqlite_database_service, batch_uid)

        # Assert
        assert unfinished == "PL1234-20-2"

    def test_an_image_taken_out_of_the_project_holds_nothing(
        self,
        sqlite_database_service: DatabaseService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        # Arrange
        _add_image(
            sqlite_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.DOWNLOADING,
            selected=False,
        )

        # Act
        unfinished = _unfinished_image(sqlite_database_service, batch_uid)

        # Assert
        assert unfinished is None
