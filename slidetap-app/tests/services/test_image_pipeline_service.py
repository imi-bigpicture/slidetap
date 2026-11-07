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

"""Tests for retrying an image that failed."""

from contextlib import nullcontext
from uuid import uuid4

import pytest
from decoy import Decoy, matchers
from decoy.matchers import Anything
from sqlalchemy.orm import Session

from slidetap.application_policy import ApplicationPolicy
from slidetap.database import DatabaseBatch, DatabaseImage
from slidetap.model import Batch, BatchStatus, ImageStatus
from slidetap.services import (
    BatchService,
    DatabaseService,
    SchemaService,
)
from slidetap.task import Scheduler
from slidetap.web.services import ImagePipelineService


@pytest.fixture()
def session(decoy: Decoy) -> Session:
    return decoy.mock(cls=Session)


@pytest.fixture()
def batch_status() -> BatchStatus:
    return BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE


@pytest.fixture()
def database_image(
    decoy: Decoy, batch: Batch, batch_status: BatchStatus
) -> DatabaseImage:
    database_image = decoy.mock(cls=DatabaseImage)
    database_batch = decoy.mock(cls=DatabaseBatch)
    decoy.when(database_batch.model).then_return(batch)
    decoy.when(database_batch.status).then_return(batch_status)
    decoy.when(database_image.batch).then_return(database_batch)
    return database_image


@pytest.fixture()
def database_service(
    decoy: Decoy, session: Session, database_image: DatabaseImage
) -> DatabaseService:
    database_service = decoy.mock(cls=DatabaseService)
    decoy.when(database_service.get_session()).then_return(nullcontext(session))
    decoy.when(database_service.get_image(session, Anything())).then_return(
        database_image
    )
    return database_service


@pytest.fixture()
def scheduler(decoy: Decoy) -> Scheduler:
    return decoy.mock(cls=Scheduler)


@pytest.fixture()
def pre_processes_separately() -> bool:
    return True


@pytest.fixture()
def image_pipeline_service(
    decoy: Decoy,
    scheduler: Scheduler,
    database_service: DatabaseService,
    pre_processes_separately: bool,
) -> ImagePipelineService:
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.can_change(matchers.Anything())).then_return(True)
    decoy.when(
        schema_service.can_change(matchers.Anything(), matchers.Anything())
    ).then_return(True)
    return ImagePipelineService(
        scheduler=scheduler,
        batch_service=decoy.mock(cls=BatchService),
        schema_service=schema_service,
        database_service=database_service,
        application_policy=ApplicationPolicy(
            pre_processes_images_separately=pre_processes_separately
        ),
    )


@pytest.mark.unittest
class TestImagePipelineService:
    def test_retry_of_storing_failed_image_stores_its_batch_again(
        self,
        decoy: Decoy,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        database_image: DatabaseImage,
        batch: Batch,
    ) -> None:
        """A retried image is reset to post-processed, and its batch stored again.

        Storing is done for a batch at a time, and the store selects images that
        are post-processed, so this is what stores the image that failed.
        """
        # Arrange
        decoy.when(database_image.status).then_return(ImageStatus.STORING_FAILED)

        # Act
        image_pipeline_service.retry(uuid4())

        # Assert
        decoy.verify(database_image.reset_as_post_processed(), times=1)
        decoy.verify(scheduler.store_images_in_batch(batch), times=1)

    def test_retry_of_storing_image_is_not_retried(
        self,
        decoy: Decoy,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        database_image: DatabaseImage,
        batch: Batch,
    ) -> None:
        """An image a worker may still be storing is left alone.

        A store left by a worker that died is recovered by the stalled job being
        retried, which stores the images it left storing again.
        """
        # Arrange
        decoy.when(database_image.status).then_return(ImageStatus.STORING)

        # Act
        image_pipeline_service.retry(uuid4())

        # Assert
        decoy.verify(database_image.reset_as_post_processed(), times=0)
        decoy.verify(scheduler.store_images_in_batch(batch), times=0)


@pytest.mark.unittest
class TestRetryOfAnImageNotProcessed:
    """A failed conversion is converted again from the image's files. An image
    that failed to download or be pre-processed is pre-processed again: by
    pre-processing it, or, where images are not pre-processed separately
    or its batch is past that, by post-processing it, which pre-processes it
    first."""

    @pytest.mark.parametrize("pre_processes_separately", [True, False])
    def test_a_failed_conversion_is_converted_from_its_files(
        self,
        decoy: Decoy,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        database_image: DatabaseImage,
    ) -> None:
        # Arrange
        decoy.when(database_image.status).then_return(
            ImageStatus.POST_PROCESSING_FAILED
        )

        # Act
        image_pipeline_service.retry(uuid4())

        # Assert
        decoy.verify(database_image.reset_as_pre_processed(), times=1)
        decoy.verify(scheduler.post_process_image(Anything()), times=1)

    @pytest.mark.parametrize(
        ["pre_processes_separately", "batch_status", "post_processes"],
        [
            (True, BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE, False),
            (True, BatchStatus.IMAGE_POST_PROCESSING_COMPLETE, True),
            (False, BatchStatus.IMAGE_POST_PROCESSING_COMPLETE, True),
        ],
    )
    @pytest.mark.parametrize(
        ["failed_status", "reset"],
        [
            (ImageStatus.DOWNLOADING_FAILED, "reset_as_not_started"),
            (ImageStatus.PRE_PROCESSING_FAILED, "reset_as_downloaded"),
        ],
    )
    def test_a_failed_pre_processing_is_retried_by_the_task_for_the_batch(
        self,
        decoy: Decoy,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        database_image: DatabaseImage,
        failed_status: ImageStatus,
        reset: str,
        post_processes: bool,
    ) -> None:
        # Arrange
        decoy.when(database_image.status).then_return(failed_status)

        # Act
        image_pipeline_service.retry(uuid4())

        # Assert
        decoy.verify(getattr(database_image, reset)(), times=1)
        decoy.verify(
            scheduler.post_process_image(Anything()),
            times=1 if post_processes else 0,
        )
        decoy.verify(
            scheduler.download_and_pre_process_image(Anything()),
            times=0 if post_processes else 1,
        )
