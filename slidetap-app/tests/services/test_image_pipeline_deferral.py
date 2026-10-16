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

"""What is left waiting when a task cannot be queued, and when there is nothing
to queue a task for."""

import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from slidetap_example import ExampleSchema

from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
    DatabaseProject,
)
from slidetap.external_interfaces import MetadataExportInterface
from slidetap.model import BatchStatus, ImageFormat, ImageStatus, Project
from slidetap.services import (
    BatchService,
    DatabaseService,
    ProjectService,
    ReviewService,
    SchemaService,
    ValidationService,
)
from slidetap.task import DeferError, Scheduler
from slidetap.web.services.image_pipeline_service import ImagePipelineService
from slidetap.web.services.metadata_export_service import MetadataExportService


class StoredBatch:
    def __init__(self, project_uid: UUID, batch_uid: UUID, dataset_uid: UUID):
        self.project_uid = project_uid
        self.batch_uid = batch_uid
        self.dataset_uid = dataset_uid


def _add_batch(
    database_service: DatabaseService, schema: ExampleSchema, status: BatchStatus
) -> StoredBatch:
    with database_service.get_session() as session:
        dataset = DatabaseDataset("dataset", schema.dataset.uid)
        session.add(dataset)
        project = DatabaseProject(
            "project",
            schema.uid,
            schema.project.uid,
            dataset.uid,
            datetime.datetime(2026, 10, 16),
        )
        session.add(project)
        batch = DatabaseBatch("batch", project.uid, datetime.datetime(2026, 10, 16))
        batch.status = status
        session.add(batch)
        session.commit()
        return StoredBatch(project.uid, batch.uid, dataset.uid)


def _add_image(
    database_service: DatabaseService,
    schema: ExampleSchema,
    stored: StoredBatch,
    status: ImageStatus,
    identifier: str,
    folder_path: str | None = None,
) -> UUID:
    with database_service.get_session() as session:
        image = DatabaseImage(
            dataset_uid=stored.dataset_uid,
            batch_uid=stored.batch_uid,
            schema_uid=schema.image.uid,
            identifier=identifier,
            format=ImageFormat.OTHER_WSI,
        )
        image.status = status
        image.selected = True
        image.folder_path = folder_path
        session.add(image)
        session.commit()
        return image.uid


def _image(database_service: DatabaseService, image_uid: UUID) -> tuple[Any, Any]:
    with database_service.get_session() as session:
        image = database_service.get_image(session, image_uid)
        return image.status, image.status_message


def _batch_status(database_service: DatabaseService, batch_uid: UUID) -> BatchStatus:
    with database_service.get_session() as session:
        return database_service.get_batch(session, batch_uid).status


@pytest.fixture()
def scheduler(decoy: Decoy) -> Scheduler:
    return decoy.mock(cls=Scheduler)


@pytest.fixture()
def schema_service(decoy: Decoy, schema: ExampleSchema) -> SchemaService:
    schema_service = decoy.mock(cls=SchemaService)
    # What of the root the pipeline reads: the item schemas, and the images.
    root = SimpleNamespace(items=dict(schema.images), images=dict(schema.images))
    decoy.when(schema_service.root_of(Anything(), Anything())).then_return(root)
    return schema_service


@pytest.fixture()
def image_pipeline_service(
    decoy: Decoy,
    scheduler: Scheduler,
    schema_service: SchemaService,
    sqlite_database_service: DatabaseService,
) -> ImagePipelineService:
    batch_service = BatchService(
        schema_service=decoy.mock(cls=SchemaService),
        validation_service=decoy.mock(cls=ValidationService),
        database_service=sqlite_database_service,
        review_service=decoy.mock(cls=ReviewService),
    )
    return ImagePipelineService(
        scheduler, batch_service, schema_service, sqlite_database_service
    )


@pytest.mark.integration
class TestImagePipelineDeferral:
    def test_a_batch_without_images_finishes_pre_processing(
        self,
        sqlite_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        schema: ExampleSchema,
    ):
        """The failure this guards against: no image task ever settles the
        batch, as there is none, and the batch is pre-processing for good."""
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.METADATA_SEARCH_COMPLETE
        )

        # Act
        batch = image_pipeline_service.pre_process_batch(stored.batch_uid)

        # Assert
        assert batch is not None
        assert batch.status == BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE

    def test_a_batch_without_images_finishes_post_processing(
        self,
        sqlite_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service,
            schema,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
        )

        # Act
        batch = image_pipeline_service.export(stored.batch_uid)

        # Assert
        assert batch is not None
        assert batch.status == BatchStatus.IMAGE_POST_PROCESSING_COMPLETE

    def test_an_image_that_cannot_be_queued_is_failed(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        """Failed rather than left waiting for a task that does not exist; the
        other image is still on its way, so the batch is not finished."""
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.METADATA_SEARCH_COMPLETE
        )
        queued = _add_image(
            sqlite_database_service,
            schema,
            stored,
            ImageStatus.NOT_STARTED,
            "PL1234-20-1",
        )
        not_queued = _add_image(
            sqlite_database_service,
            schema,
            stored,
            ImageStatus.NOT_STARTED,
            "PL1234-20-2",
        )
        decoy.when(scheduler.pre_process_images(Anything())).then_raise(
            DeferError({not_queued: ConnectionError("Queue unreachable")})
        )

        # Act
        batch = image_pipeline_service.pre_process_batch(stored.batch_uid)

        # Assert
        status, message = _image(sqlite_database_service, not_queued)
        assert status == ImageStatus.DOWNLOADING_FAILED
        assert message is not None and "Queue unreachable" in message
        assert _image(sqlite_database_service, queued)[0] == ImageStatus.NOT_STARTED
        assert batch is not None
        assert batch.status == BatchStatus.IMAGE_PRE_PROCESSING

    def test_a_batch_whose_images_cannot_be_queued_settles(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service,
            schema,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
        )
        image_uid = _add_image(
            sqlite_database_service,
            schema,
            stored,
            ImageStatus.PRE_PROCESSED,
            "PL1234-20-1",
        )
        decoy.when(scheduler.post_process_images(Anything())).then_raise(
            DeferError({image_uid: ConnectionError("Queue unreachable")})
        )

        # Act
        batch = image_pipeline_service.export(stored.batch_uid)

        # Assert
        assert (
            _image(sqlite_database_service, image_uid)[0]
            == ImageStatus.POST_PROCESSING_FAILED
        )
        assert batch is not None
        assert batch.status == BatchStatus.IMAGE_POST_PROCESSING_COMPLETE

    def test_a_retry_that_cannot_be_queued_leaves_the_image_failed(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service,
            schema,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
        )
        image_uid = _add_image(
            sqlite_database_service,
            schema,
            stored,
            ImageStatus.DOWNLOADING_FAILED,
            "PL1234-20-1",
        )
        decoy.when(scheduler.download_and_pre_process_image(Anything())).then_raise(
            ConnectionError("Queue unreachable")
        )

        # Act
        image_pipeline_service.retry(image_uid)

        # Assert
        status, message = _image(sqlite_database_service, image_uid)
        assert status == ImageStatus.DOWNLOADING_FAILED
        assert message is not None and "Queue unreachable" in message

    def test_a_store_that_cannot_be_queued_raises_after_the_others(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(sqlite_database_service, schema, BatchStatus.LOCKED)
        decoy.when(scheduler.store_images_in_batch(Anything())).then_raise(
            ConnectionError("Queue unreachable")
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Queue unreachable"):
            image_pipeline_service.store_project(stored.project_uid)
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_STORING
        )


class TestMetadataExportDeferral:
    def test_an_export_that_cannot_be_queued_is_reverted(
        self, decoy: Decoy, scheduler: Scheduler, project: Project
    ):
        # Arrange
        project_service = decoy.mock(cls=ProjectService)
        decoy.when(scheduler.metadata_project_export(project)).then_raise(
            ConnectionError("Queue unreachable")
        )
        metadata_export_service = MetadataExportService(
            scheduler,
            project_service,
            decoy.mock(cls=DatabaseService),
            decoy.mock(cls=SchemaService),
            decoy.mock(cls=MetadataExportInterface),
        )

        # Act & Assert
        with pytest.raises(ConnectionError):
            metadata_export_service.export(project)
        decoy.verify(project_service.revert_export(project.uid), times=1)
