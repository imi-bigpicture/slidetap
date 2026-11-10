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
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything, HasAttributes
from slidetap_example import ExampleSchema

from slidetap.application_policy import ApplicationPolicy
from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
    DatabaseProject,
)
from slidetap.external_interfaces import MetadataExportInterface
from slidetap.model import (
    Batch,
    BatchStatus,
    ImageFormat,
    ImageStatus,
    NotAllowedActionError,
    Project,
)
from slidetap.services import (
    BatchService,
    DatabaseService,
    ItemService,
    ProjectService,
    ReviewService,
    SchemaService,
    ValidationService,
    VerificationService,
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
    stored_database_service: DatabaseService,
) -> ImagePipelineService:
    batch_service = BatchService(
        schema_service=schema_service,
        validation_service=decoy.mock(cls=ValidationService),
        database_service=stored_database_service,
        review_service=decoy.mock(cls=ReviewService),
        verification_service=decoy.mock(cls=VerificationService),
        application_policy=ApplicationPolicy(),
    )
    return ImagePipelineService(
        scheduler,
        batch_service,
        schema_service,
        stored_database_service,
        application_policy=ApplicationPolicy(),
    )


@pytest.mark.integration
class TestImagePipelineDeferral:
    def test_a_batch_without_images_finishes_pre_processing(
        self,
        stored_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        schema: ExampleSchema,
    ):
        """The failure this guards against: no image task ever settles the
        batch, as there is none, and the batch is pre-processing for good."""
        # Arrange
        stored = _add_batch(
            stored_database_service, schema, BatchStatus.METADATA_SEARCH_COMPLETE
        )

        # Act
        batch = image_pipeline_service.pre_process_batch(stored.batch_uid)

        # Assert
        assert batch is not None
        assert batch.status == BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE

    def test_a_batch_without_images_finishes_post_processing(
        self,
        stored_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            stored_database_service,
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
        stored_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        """Failed rather than left waiting for a task that does not exist; the
        other image is still on its way, so the batch is not finished."""
        # Arrange
        stored = _add_batch(
            stored_database_service, schema, BatchStatus.METADATA_SEARCH_COMPLETE
        )
        queued = _add_image(
            stored_database_service,
            schema,
            stored,
            ImageStatus.NOT_STARTED,
            "PL1234-20-1",
        )
        not_queued = _add_image(
            stored_database_service,
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
        status, message = _image(stored_database_service, not_queued)
        assert status == ImageStatus.DOWNLOADING_FAILED
        assert message is not None and "Queue unreachable" in message
        assert _image(stored_database_service, queued)[0] == ImageStatus.NOT_STARTED
        assert batch is not None
        assert batch.status == BatchStatus.IMAGE_PRE_PROCESSING

    def test_a_batch_whose_images_cannot_be_queued_settles(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            stored_database_service,
            schema,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
        )
        image_uid = _add_image(
            stored_database_service,
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
            _image(stored_database_service, image_uid)[0]
            == ImageStatus.POST_PROCESSING_FAILED
        )
        assert batch is not None
        assert batch.status == BatchStatus.IMAGE_POST_PROCESSING_COMPLETE

    def test_a_retry_that_cannot_be_queued_leaves_the_image_failed(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            stored_database_service,
            schema,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
        )
        image_uid = _add_image(
            stored_database_service,
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
        status, message = _image(stored_database_service, image_uid)
        assert status == ImageStatus.DOWNLOADING_FAILED
        assert message is not None and "Queue unreachable" in message

    def test_a_store_that_cannot_be_queued_raises_after_the_others(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(stored_database_service, schema, BatchStatus.LOCKED)
        decoy.when(scheduler.store_images_in_batch(Anything())).then_raise(
            ConnectionError("Queue unreachable")
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Queue unreachable"):
            image_pipeline_service.store_project(stored.project_uid)
        assert (
            _batch_status(stored_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_STORING
        )

    def test_a_project_with_a_batch_stored_alone_is_not_stored_whole(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        """Its bundle would name items whose images are in the batch's bundle."""
        # Arrange
        stored = _add_batch(stored_database_service, schema, BatchStatus.LOCKED)
        with stored_database_service.get_session() as session:
            alone = DatabaseBatch(
                "alone", stored.project_uid, datetime.datetime(2026, 10, 28)
            )
            alone.status = BatchStatus.EXPORTED
            alone.storage_folder = "BATCH_alone"
            session.add(alone)
            session.commit()

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="stored on its own"):
            image_pipeline_service.store_project(stored.project_uid)
        decoy.verify(scheduler.store_images_in_batch(Anything()), times=0)
        assert (
            _batch_status(stored_database_service, stored.batch_uid)
            == BatchStatus.LOCKED
        )


@pytest.fixture()
def not_separately_pipeline_service(
    decoy: Decoy,
    scheduler: Scheduler,
    schema_service: SchemaService,
    stored_database_service: DatabaseService,
) -> ImagePipelineService:
    """The pipeline of an application that does not pre-process images
    separately."""
    policy = ApplicationPolicy(pre_processes_images_separately=False)
    batch_service = BatchService(
        schema_service=schema_service,
        validation_service=decoy.mock(cls=ValidationService),
        database_service=stored_database_service,
        review_service=decoy.mock(cls=ReviewService),
        verification_service=decoy.mock(cls=VerificationService),
        application_policy=policy,
    )
    return ImagePipelineService(
        scheduler,
        batch_service,
        schema_service,
        stored_database_service,
        application_policy=policy,
    )


@pytest.mark.integration
class TestNotPreProcessedSeparately:
    @pytest.mark.parametrize(
        ("status", "failed"),
        [
            (ImageStatus.NOT_STARTED, ImageStatus.DOWNLOADING_FAILED),
            (ImageStatus.DOWNLOADED, ImageStatus.PRE_PROCESSING_FAILED),
            (ImageStatus.PRE_PROCESSED, ImageStatus.POST_PROCESSING_FAILED),
        ],
    )
    def test_an_image_that_cannot_be_queued_fails_at_its_step(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        not_separately_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
        status: ImageStatus,
        failed: ImageStatus,
    ):
        """So that a retry goes on from where it is, rather than converting an
        image that was never downloaded."""
        # Arrange
        stored = _add_batch(
            stored_database_service, schema, BatchStatus.METADATA_SEARCH_COMPLETE
        )
        image_uid = _add_image(
            stored_database_service, schema, stored, status, "PL1234-20-1"
        )
        decoy.when(scheduler.post_process_images(Anything())).then_raise(
            DeferError({image_uid: ConnectionError("Queue unreachable")})
        )

        # Act
        batch = not_separately_pipeline_service.export(stored.batch_uid)

        # Assert
        assert _image(stored_database_service, image_uid)[0] == failed
        assert batch is not None
        assert batch.status == BatchStatus.IMAGE_POST_PROCESSING_COMPLETE

    @pytest.mark.parametrize(
        "batch_status",
        [
            BatchStatus.METADATA_SEARCH_COMPLETE,
            BatchStatus.IMAGE_PRE_PROCESSING,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
        ],
    )
    @pytest.mark.parametrize(
        ("failed", "set_back"),
        [
            (ImageStatus.DOWNLOADING_FAILED, ImageStatus.NOT_STARTED),
            (ImageStatus.PRE_PROCESSING_FAILED, ImageStatus.DOWNLOADED),
        ],
    )
    def test_a_retry_before_the_batch_is_post_processed_only_sets_it_back(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        not_separately_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
        batch_status: BatchStatus,
        failed: ImageStatus,
        set_back: ImageStatus,
    ):
        """Post-processing the batch takes it on, so that it is not converted
        before the batch is curated for it."""
        # Arrange
        stored = _add_batch(stored_database_service, schema, batch_status)
        image_uid = _add_image(
            stored_database_service, schema, stored, failed, "PL1234-20-1"
        )

        # Act
        not_separately_pipeline_service.retry(image_uid)

        # Assert
        assert _image(stored_database_service, image_uid)[0] == set_back
        decoy.verify(scheduler.post_process_image(Anything()), times=0)
        decoy.verify(scheduler.download_and_pre_process_image(Anything()), times=0)

    def test_a_retry_while_the_batch_is_post_processed_converts_it(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        not_separately_pipeline_service: ImagePipelineService,
        scheduler: Scheduler,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            stored_database_service, schema, BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
        )
        image_uid = _add_image(
            stored_database_service,
            schema,
            stored,
            ImageStatus.DOWNLOADING_FAILED,
            "PL1234-20-1",
        )

        # Act
        not_separately_pipeline_service.retry(image_uid)

        # Assert
        assert _image(stored_database_service, image_uid)[0] == ImageStatus.NOT_STARTED
        decoy.verify(
            scheduler.post_process_image(HasAttributes({"uid": image_uid})), times=1
        )


@pytest.mark.unittest
class TestMetadataExportDeferral:
    @pytest.fixture()
    def project_service(self, decoy: Decoy) -> ProjectService:
        return decoy.mock(cls=ProjectService)

    @pytest.fixture()
    def batch_service(self, decoy: Decoy) -> BatchService:
        return decoy.mock(cls=BatchService)

    @pytest.fixture()
    def item_service(self, decoy: Decoy) -> ItemService:
        return decoy.mock(cls=ItemService)

    @pytest.fixture()
    def metadata_export_interface(self, decoy: Decoy) -> MetadataExportInterface:
        return decoy.mock(cls=MetadataExportInterface)

    @pytest.fixture()
    def metadata_export_service(
        self,
        decoy: Decoy,
        scheduler: Scheduler,
        project_service: ProjectService,
        batch_service: BatchService,
        item_service: ItemService,
        metadata_export_interface: MetadataExportInterface,
    ) -> MetadataExportService:
        return MetadataExportService(
            scheduler=scheduler,
            project_service=project_service,
            batch_service=batch_service,
            item_service=item_service,
            database_service=decoy.mock(cls=DatabaseService),
            schema_service=decoy.mock(cls=SchemaService),
            metadata_export_interface=metadata_export_interface,
            application_policy=ApplicationPolicy(allows_batch_export=True),
        )

    @pytest.fixture()
    def batch(self, project: Project) -> Batch:
        return Batch(
            uid=uuid4(),
            name="batch",
            status=BatchStatus.LOCKED,
            project_uid=project.uid,
            is_default=False,
            created=datetime.datetime(2026, 10, 28),
        )

    @pytest.fixture()
    def exportable(
        self,
        decoy: Decoy,
        project: Project,
        project_service: ProjectService,
        batch_service: BatchService,
        item_service: ItemService,
        metadata_export_interface: MetadataExportInterface,
        batch: Batch,
    ) -> Batch:
        """The batch, as the export exports it on its own."""
        decoy.when(batch_service.get(batch.uid)).then_return(batch)
        decoy.when(metadata_export_interface.batch_export_refusal(batch)).then_return(
            None
        )
        decoy.when(project_service.get(project.uid)).then_return(project)
        decoy.when(
            item_service.items_missing_pseudonym(
                project.dataset_uid, batch_uid=batch.uid
            )
        ).then_return(0)
        return batch

    def test_an_export_that_cannot_be_queued_is_reverted(
        self,
        decoy: Decoy,
        scheduler: Scheduler,
        project: Project,
        project_service: ProjectService,
        metadata_export_service: MetadataExportService,
    ):
        # Arrange
        decoy.when(scheduler.metadata_project_export(project)).then_raise(
            ConnectionError("Queue unreachable")
        )

        # Act & Assert
        with pytest.raises(ConnectionError):
            metadata_export_service.export(project)
        decoy.verify(project_service.revert_export(project.uid), times=1)

    def test_a_batch_export_that_cannot_be_queued_is_reverted_with_why(
        self,
        decoy: Decoy,
        scheduler: Scheduler,
        batch_service: BatchService,
        metadata_export_service: MetadataExportService,
        exportable: Batch,
    ):
        # Arrange
        decoy.when(batch_service.set_as_exporting(exportable.uid)).then_return(
            exportable
        )
        decoy.when(scheduler.metadata_batch_export(exportable)).then_raise(
            ConnectionError("Queue unreachable")
        )

        # Act & Assert
        with pytest.raises(ConnectionError):
            metadata_export_service.export_batch(exportable.uid)
        decoy.verify(
            batch_service.revert_export(
                exportable.uid,
                message="Export could not be queued: Queue unreachable",
            ),
            times=1,
        )

    def test_a_batch_is_stored_alone_with_what_it_is_exported_with(
        self,
        decoy: Decoy,
        scheduler: Scheduler,
        batch_service: BatchService,
        metadata_export_interface: MetadataExportInterface,
        metadata_export_service: MetadataExportService,
        exportable: Batch,
    ):
        # Arrange
        shared = [uuid4()]
        decoy.when(
            metadata_export_interface.batch_shared_items(exportable)
        ).then_return(shared)
        decoy.when(
            batch_service.set_as_storing_alone(exportable.uid, shared)
        ).then_return(exportable)

        # Act
        metadata_export_service.store_batch(exportable.uid)

        # Assert
        decoy.verify(scheduler.store_images_in_batch(exportable), times=1)

    def test_a_batch_the_export_refuses_is_neither_stored_nor_exported(
        self,
        decoy: Decoy,
        batch_service: BatchService,
        metadata_export_interface: MetadataExportInterface,
        metadata_export_service: MetadataExportService,
        exportable: Batch,
    ):
        # Arrange
        decoy.when(
            metadata_export_interface.batch_export_refusal(exportable)
        ).then_return("A case of it has a specimen in another batch.")

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="specimen in another batch"):
            metadata_export_service.store_batch(exportable.uid)
        with pytest.raises(NotAllowedActionError, match="specimen in another batch"):
            metadata_export_service.export_batch(exportable.uid)
        decoy.verify(
            batch_service.set_as_storing_alone(Anything(), Anything()), times=0
        )
        decoy.verify(batch_service.set_as_exporting(Anything()), times=0)

    def test_an_application_that_does_not_export_batches_refuses_every_batch(
        self,
        decoy: Decoy,
        scheduler: Scheduler,
        project_service: ProjectService,
        batch_service: BatchService,
        item_service: ItemService,
        metadata_export_interface: MetadataExportInterface,
        exportable: Batch,
    ):
        # Arrange
        metadata_export_service = MetadataExportService(
            scheduler=scheduler,
            project_service=project_service,
            batch_service=batch_service,
            item_service=item_service,
            database_service=decoy.mock(cls=DatabaseService),
            schema_service=decoy.mock(cls=SchemaService),
            metadata_export_interface=metadata_export_interface,
            application_policy=ApplicationPolicy(),
        )

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="does not export a batch"):
            metadata_export_service.store_batch(exportable.uid)
        with pytest.raises(NotAllowedActionError, match="does not export a batch"):
            metadata_export_service.export_batch(exportable.uid)
        decoy.verify(
            batch_service.set_as_storing_alone(Anything(), Anything()), times=0
        )
        decoy.verify(batch_service.set_as_exporting(Anything()), times=0)

    def test_a_batch_with_an_item_without_a_pseudonym_is_refused(
        self,
        decoy: Decoy,
        project: Project,
        item_service: ItemService,
        metadata_export_service: MetadataExportService,
        exportable: Batch,
    ):
        # Arrange
        decoy.when(
            item_service.items_missing_pseudonym(
                project.dataset_uid, batch_uid=exportable.uid
            )
        ).then_return(2)

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="2 items .* no pseudonym"):
            metadata_export_service.export_batch(exportable.uid)
