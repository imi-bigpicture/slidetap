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

"""Tests for retrying an image that failed to store."""

from contextlib import nullcontext
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from sqlalchemy.orm import Session

from slidetap.database import DatabaseBatch, DatabaseImage
from slidetap.model import Batch, ImageStatus, RootSchema
from slidetap.services import BatchService, DatabaseService, SchemaService
from slidetap.task import Scheduler
from slidetap.web.services import ImagePipelineService


@pytest.fixture()
def session(decoy: Decoy) -> Session:
    return decoy.mock(cls=Session)


@pytest.fixture()
def database_image(decoy: Decoy, batch: Batch) -> DatabaseImage:
    database_image = decoy.mock(cls=DatabaseImage)
    database_batch = decoy.mock(cls=DatabaseBatch)
    decoy.when(database_batch.model).then_return(batch)
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
def image_pipeline_service(
    decoy: Decoy,
    scheduler: Scheduler,
    database_service: DatabaseService,
    schema: RootSchema,
) -> ImagePipelineService:
    return ImagePipelineService(
        scheduler=scheduler,
        batch_service=decoy.mock(cls=BatchService),
        schema_service=decoy.mock(cls=SchemaService),
        database_service=database_service,
        root_schema=schema,
    )


@pytest.mark.unittest
class TestImagePipelineService:
    @pytest.mark.asyncio
    async def test_retry_of_storing_failed_image_stores_its_batch_again(
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
        await image_pipeline_service.retry(uuid4())

        # Assert
        decoy.verify(database_image.reset_as_post_processed(), times=1)
        decoy.verify(await scheduler.store_images_in_batch(batch), times=1)

    @pytest.mark.asyncio
    async def test_retry_of_storing_image_is_not_retried(
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
        await image_pipeline_service.retry(uuid4())

        # Assert
        decoy.verify(database_image.reset_as_post_processed(), times=0)
        decoy.verify(await scheduler.store_images_in_batch(batch), times=0)
