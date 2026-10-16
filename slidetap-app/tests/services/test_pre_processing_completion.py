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

import datetime
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything

from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
    DatabaseProject,
)
from slidetap.model import BatchStatus, ImageFormat, ImageStatus
from slidetap.services import (
    BatchService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
)
from slidetap.services.batch_service import PRE_PROCESSING_SETTLED


@pytest.fixture()
def batch_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def dataset_uid(stored_database_service: DatabaseService) -> UUID:
    with stored_database_service.get_session() as session:
        dataset = DatabaseDataset("dataset", uuid4())
        session.add(dataset)
        session.commit()
        return dataset.uid


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


def _add_batch(
    database_service: DatabaseService,
    batch_uid: UUID,
    dataset_uid: UUID,
    status: BatchStatus,
) -> None:
    with database_service.get_session() as session:
        project = DatabaseProject(
            "project",
            uuid4(),
            uuid4(),
            dataset_uid,
            datetime.datetime(2026, 10, 13),
        )
        session.add(project)
        batch = DatabaseBatch(
            "batch", project.uid, datetime.datetime(2026, 10, 13), uid=batch_uid
        )
        batch.status = status
        session.add(batch)


def _batch_status(database_service: DatabaseService, batch_uid: UUID) -> BatchStatus:
    with database_service.get_session() as session:
        return database_service.get_batch(session, batch_uid).status


@pytest.fixture()
def review_service(decoy: Decoy) -> ReviewService:
    return decoy.mock(cls=ReviewService)


@pytest.fixture()
def batch_service(
    decoy: Decoy,
    stored_database_service: DatabaseService,
    review_service: ReviewService,
) -> BatchService:
    return BatchService(
        schema_service=decoy.mock(cls=SchemaService),
        validation_service=decoy.mock(cls=ValidationService),
        database_service=stored_database_service,
        review_service=review_service,
    )


@pytest.mark.integration
class TestFinishPreProcessingIfSettled:
    def test_images_settling_together_finish_the_batch_once(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        batch_service: BatchService,
        review_service: ReviewService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        """The failure this guards against: two images settle at about the same
        time, both find nothing left to wait for, and the second to set the
        batch as pre-processed is refused as the batch already is."""
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_PRE_PROCESSING,
        )
        for identifier in ("PL1234-20-1", "PL1234-20-2"):
            _add_image(
                stored_database_service,
                batch_uid,
                dataset_uid,
                identifier,
                ImageStatus.PRE_PROCESSED,
            )

        # Act
        batch_service.finish_pre_processing_if_settled(batch_uid)
        batch_service.finish_pre_processing_if_settled(batch_uid)

        # Assert
        assert (
            _batch_status(stored_database_service, batch_uid)
            == BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )
        decoy.verify(
            review_service.flag_invalid_review_units(
                dataset_uid, batch_uid, session=Anything()
            ),
            times=1,
        )

    def test_a_batch_is_finished_by_an_image_that_failed(
        self,
        stored_database_service: DatabaseService,
        batch_service: BatchService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_PRE_PROCESSING,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.PRE_PROCESSED,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.PRE_PROCESSING_FAILED,
        )

        # Act
        batch_service.finish_pre_processing_if_settled(batch_uid)

        # Assert
        assert (
            _batch_status(stored_database_service, batch_uid)
            == BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )

    def test_a_batch_waiting_for_an_image_is_not_finished(
        self,
        stored_database_service: DatabaseService,
        batch_service: BatchService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_PRE_PROCESSING,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.PRE_PROCESSED,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.DOWNLOADING,
        )

        # Act
        batch_service.finish_pre_processing_if_settled(batch_uid)

        # Assert
        assert (
            _batch_status(stored_database_service, batch_uid)
            == BatchStatus.IMAGE_PRE_PROCESSING
        )

    def test_an_image_retried_after_the_batch_moved_on_leaves_the_batch(
        self,
        stored_database_service: DatabaseService,
        batch_service: BatchService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_POST_PROCESSING,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.PRE_PROCESSED,
        )

        # Act
        batch_service.finish_pre_processing_if_settled(batch_uid)

        # Assert
        assert (
            _batch_status(stored_database_service, batch_uid)
            == BatchStatus.IMAGE_POST_PROCESSING
        )


@pytest.mark.integration
class TestPreProcessingCompletion:
    def test_a_batch_finishes_around_an_image_that_failed_to_download(
        self,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        """The failure this guards against: an image the source would not hand
        over holds the batch at pre-processing for good, and every case in it
        goes unflagged, since flagging is what finishing pre-processing does.
        """
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_PRE_PROCESSING,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.PRE_PROCESSED,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.DOWNLOADING_FAILED,
        )

        # Act
        unfinished = _unfinished_image(stored_database_service, batch_uid)

        # Assert
        assert unfinished is None

    def test_an_image_still_on_its_way_holds_the_batch(
        self,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        """The other half of it: a batch is not finished while an image is
        still going to arrive."""
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_PRE_PROCESSING,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.PRE_PROCESSED,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.DOWNLOADING,
        )

        # Act
        unfinished = _unfinished_image(stored_database_service, batch_uid)

        # Assert
        assert unfinished == "PL1234-20-2"

    def test_an_image_taken_out_of_the_project_holds_nothing(
        self,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_PRE_PROCESSING,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.DOWNLOADING,
            selected=False,
        )

        # Act
        unfinished = _unfinished_image(stored_database_service, batch_uid)

        # Assert
        assert unfinished is None


@pytest.mark.integration
class TestFirstImageForBatch:
    def test_an_image_in_any_of_the_included_statuses_is_found(
        self,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        """The failure this guards against: each included status narrowing the
        query on its own, so that asking for more than one finds nothing."""
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_PRE_PROCESSING,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.STORED,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-2",
            ImageStatus.POST_PROCESSING_FAILED,
        )

        # Act
        with stored_database_service.get_session() as session:
            image = stored_database_service.get_first_image_for_batch(
                session,
                batch_uid=batch_uid,
                include_status=[
                    ImageStatus.STORING_FAILED,
                    ImageStatus.POST_PROCESSING_FAILED,
                ],
            )
            identifier = image.identifier if image is not None else None

        # Assert
        assert identifier == "PL1234-20-2"

    def test_an_image_in_none_of_the_included_statuses_is_not_found(
        self,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        dataset_uid: UUID,
    ) -> None:
        # Arrange
        _add_batch(
            stored_database_service,
            batch_uid,
            dataset_uid,
            BatchStatus.IMAGE_PRE_PROCESSING,
        )
        _add_image(
            stored_database_service,
            batch_uid,
            dataset_uid,
            "PL1234-20-1",
            ImageStatus.STORED,
        )

        # Act
        with stored_database_service.get_session() as session:
            image = stored_database_service.get_first_image_for_batch(
                session,
                batch_uid=batch_uid,
                include_status=[
                    ImageStatus.STORING_FAILED,
                    ImageStatus.POST_PROCESSING_FAILED,
                ],
            )

        # Assert
        assert image is None
