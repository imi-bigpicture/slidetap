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

"""Tests for completing a batch that has stored its images."""

from contextlib import nullcontext
from uuid import uuid4

import pytest
from decoy import Decoy
from sqlalchemy.orm import Session

from slidetap.database import DatabaseBatch, DatabaseImage, NotAllowedActionError
from slidetap.model import BatchStatus, ImageStatus
from slidetap.services import (
    BatchService,
    DatabaseService,
    SchemaService,
    ValidationService,
)


@pytest.fixture()
def session(decoy: Decoy) -> Session:
    return decoy.mock(cls=Session)


@pytest.fixture()
def database_batch(decoy: Decoy) -> DatabaseBatch:
    database_batch = decoy.mock(cls=DatabaseBatch)
    decoy.when(database_batch.uid).then_return(uuid4())
    decoy.when(database_batch.image_storing).then_return(True)
    return database_batch


@pytest.fixture()
def database_service(
    decoy: Decoy, session: Session, database_batch: DatabaseBatch
) -> DatabaseService:
    database_service = decoy.mock(cls=DatabaseService)
    decoy.when(database_service.get_session(session)).then_return(nullcontext(session))
    decoy.when(database_service.get_batch(session, database_batch)).then_return(
        database_batch
    )
    return database_service


@pytest.fixture()
def batch_service(
    decoy: Decoy,
    database_service: DatabaseService,
) -> BatchService:
    return BatchService(
        schema_service=decoy.mock(cls=SchemaService),
        validation_service=decoy.mock(cls=ValidationService),
        database_service=database_service,
    )


@pytest.mark.unittest
class TestBatchService:
    def test_batch_with_an_image_that_failed_to_store_is_not_completed(
        self,
        decoy: Decoy,
        batch_service: BatchService,
        database_service: DatabaseService,
        database_batch: DatabaseBatch,
        session: Session,
    ) -> None:
        """A batch missing an image from the outbox is not completed.

        The image that failed to store is not in the dataset in the outbox, so
        completing the batch would record a dataset as complete that is missing an
        image. The image is stored by retrying it, or excluded from the batch by
        deselecting it.
        """
        # Arrange
        failed_image = decoy.mock(cls=DatabaseImage)
        decoy.when(failed_image.uid).then_return(uuid4())
        decoy.when(
            database_service.get_first_image_for_batch(
                session,
                batch_uid=database_batch.uid,
                include_status=[ImageStatus.STORING_FAILED],
                selected=True,
            )
        ).then_return(failed_image)

        # Act & Assert
        with pytest.raises(NotAllowedActionError):
            batch_service.set_as_completed(database_batch, session)
        assert database_batch.status != BatchStatus.COMPLETED

    def test_image_that_failed_to_store_is_none_when_all_images_are_stored(
        self,
        decoy: Decoy,
        batch_service: BatchService,
        database_service: DatabaseService,
        database_batch: DatabaseBatch,
        session: Session,
    ) -> None:
        """A batch whose images are all stored has no image that failed to store."""
        # Arrange
        decoy.when(
            database_service.get_first_image_for_batch(
                session,
                batch_uid=database_batch.uid,
                include_status=[ImageStatus.STORING_FAILED],
                selected=True,
            )
        ).then_return(None)

        # Act
        failed_image = batch_service.image_that_failed_to_store(database_batch, session)

        # Assert
        assert failed_image is None
