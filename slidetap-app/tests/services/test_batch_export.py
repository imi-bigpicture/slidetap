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

"""Storing and exporting a batch on its own, against a real database.

The shared item throughout is a patient with a case in each of two batches.
"""

import datetime
from collections.abc import Callable
from uuid import UUID

import pytest
from decoy import Decoy
from slidetap_example import ExampleSchema
from sqlalchemy.orm import Session

from slidetap.application_policy import ApplicationPolicy
from slidetap.database import DatabaseImage, DatabaseSample
from slidetap.model import (
    BatchCreate,
    BatchStatus,
    Dataset,
    ImageFormat,
    ImageStatus,
    NotAllowedActionError,
    Project,
    ProjectStatus,
)
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    MapperService,
    MigrationService,
    ProjectService,
    ReviewService,
    SchemaService,
    StorageService,
    ValidationService,
    VerificationService,
)


@pytest.fixture()
def schema_service(
    schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
) -> SchemaService:
    return schema_service_of(schema)


@pytest.fixture()
def batch_service(
    schema_service: SchemaService,
    stored_database_service: DatabaseService,
) -> BatchService:
    validation_service = ValidationService(
        schema_service, stored_database_service, application_policy=ApplicationPolicy()
    )
    review_service = ReviewService(
        schema_service, validation_service, stored_database_service
    )
    return BatchService(
        schema_service,
        validation_service,
        stored_database_service,
        review_service,
        VerificationService(schema_service, stored_database_service, review_service),
        application_policy=ApplicationPolicy(),
    )


@pytest.fixture()
def project_service(
    decoy: Decoy,
    schema_service: SchemaService,
    stored_database_service: DatabaseService,
) -> ProjectService:
    return ProjectService(
        attribute_service=decoy.mock(cls=AttributeService),
        batch_service=decoy.mock(cls=BatchService),
        schema_service=schema_service,
        validation_service=ValidationService(
            schema_service,
            stored_database_service,
            application_policy=ApplicationPolicy(),
        ),
        mapper_service=decoy.mock(cls=MapperService),
        database_service=stored_database_service,
        storage_service=decoy.mock(cls=StorageService),
        migration_service=decoy.mock(cls=MigrationService),
    )


@pytest.fixture()
def batches(
    stored_database_service: DatabaseService,
    dataset: Dataset,
    project: Project,
) -> tuple[UUID, UUID]:
    """Batch A, locked and ready to go on its own, and batch B, in curation."""
    with stored_database_service.get_session() as session:
        stored_database_service.add_dataset(session, dataset)
        stored_database_service.add_project(session, project)
        first = stored_database_service.add_batch(
            session, BatchCreate(name="A", project_uid=project.uid)
        )
        first.created = datetime.datetime(2026, 1, 1)
        first.status = BatchStatus.LOCKED
        second = stored_database_service.add_batch(
            session, BatchCreate(name="B", project_uid=project.uid)
        )
        second.created = datetime.datetime(2026, 2, 1)
        second.status = BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
        session.commit()
        return first.uid, second.uid


def sample(
    session: Session,
    dataset_uid: UUID,
    batch_uid: UUID,
    schema_uid: UUID,
    identifier: str,
    parents: list[DatabaseSample] | None = None,
    valid: bool = True,
) -> DatabaseSample:
    stored = DatabaseSample(
        dataset_uid, batch_uid, schema_uid, identifier, parents=parents
    )
    stored.valid_attributes = valid
    stored.valid_relations = valid
    session.add(stored)
    session.flush()
    return stored


def set_status(
    database_service: DatabaseService, batch_uid: UUID, status: BatchStatus
) -> None:
    with database_service.get_session() as session:
        database_service.get_batch(session, batch_uid).status = status
        session.commit()


@pytest.mark.integration
class TestStoringAlone:
    def test_a_locked_batch_is_stored_into_a_folder_of_its_own(
        self,
        batch_service: BatchService,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, _ = batches

        # Act
        stored = batch_service.set_as_storing_alone(first)

        # Assert
        assert stored.status == BatchStatus.IMAGE_STORING
        assert stored.storage_folder == "BATCH_A"
        assert stored.stored_alone

    def test_a_shared_item_is_handed_over_and_locked(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        """The patient is locked with the batch, whatever its old batch does."""
        # Arrange
        first, second = batches
        with stored_database_service.get_session() as session:
            patient = sample(
                session, dataset.uid, second, schema.patient_schema_uid, "patient"
            )
            sample(
                session,
                dataset.uid,
                first,
                schema.case_schema_uid,
                "case A",
                parents=[patient],
            )
            patient_uid = patient.uid
            session.commit()

        # Act
        batch_service.set_as_storing_alone(first, [patient_uid])

        # Assert
        with stored_database_service.get_session() as session:
            stored = stored_database_service.get_item(session, patient_uid)
            assert stored.batch_uid == first
            assert stored.locked

    def test_a_shared_item_that_is_not_valid_refuses_the_batch(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        with stored_database_service.get_session() as session:
            patient = sample(
                session,
                dataset.uid,
                second,
                schema.patient_schema_uid,
                "patient",
                valid=False,
            )
            patient_uid = patient.uid
            session.commit()

        # Act
        with pytest.raises(NotAllowedActionError, match="not valid .*patient"):
            batch_service.set_as_storing_alone(first, [patient_uid])

        # Assert
        with stored_database_service.get_session() as session:
            assert stored_database_service.get_item(session, patient_uid).batch_uid == (
                second
            )
            batch = stored_database_service.get_batch(session, first)
            assert batch.status == BatchStatus.LOCKED
            assert batch.storage_folder is None

    def test_a_shared_item_of_a_batch_stored_on_its_own_stays_there(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        """It went out with that batch and stays locked there."""
        # Arrange
        first, second = batches
        batch_service.set_as_storing_alone(first)
        with stored_database_service.get_session() as session:
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient"
            )
            patient_uid = patient.uid
            session.commit()
        set_status(stored_database_service, second, BatchStatus.LOCKED)

        # Act
        batch_service.set_as_storing_alone(second, [patient_uid])

        # Assert
        with stored_database_service.get_session() as session:
            assert stored_database_service.get_item(session, patient_uid).batch_uid == (
                first
            )

    def test_a_batch_not_locked_is_refused(
        self,
        batch_service: BatchService,
        batches: tuple[UUID, UUID],
    ):
        _, second = batches

        with pytest.raises(NotAllowedActionError, match="LOCKED"):
            batch_service.set_as_storing_alone(second)

    def test_a_batch_stored_with_the_project_refuses_storing_alone(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        batches: tuple[UUID, UUID],
    ):
        """The project bundle would name items whose images are not in it."""
        # Arrange
        first, second = batches
        set_status(stored_database_service, second, BatchStatus.COMPLETED)

        # Act
        with pytest.raises(NotAllowedActionError, match="stored with the project"):
            batch_service.set_as_storing_alone(first)

    def test_a_batch_stored_alone_refuses_storing_with_the_project(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        batch_service.set_as_storing_alone(first)
        set_status(stored_database_service, second, BatchStatus.LOCKED)

        # Act
        with pytest.raises(NotAllowedActionError, match="stored on its own"):
            batch_service.set_as_storing(second)

    def test_storing_alone_again_resumes_it(
        self,
        batch_service: BatchService,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, _ = batches
        batch_service.set_as_storing_alone(first)

        # Act
        stored = batch_service.set_as_storing_alone(first)

        # Assert
        assert stored.status == BatchStatus.IMAGE_STORING
        assert stored.storage_folder == "BATCH_A"

    def test_batches_of_the_same_name_get_folders_of_their_own(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        project: Project,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, _ = batches
        with stored_database_service.get_session() as session:
            same_name = stored_database_service.add_batch(
                session, BatchCreate(name="A", project_uid=project.uid)
            )
            same_name.status = BatchStatus.LOCKED
            session.commit()
            same_name_uid = same_name.uid
        batch_service.set_as_storing_alone(first)

        # Act
        stored = batch_service.set_as_storing_alone(same_name_uid)

        # Assert
        assert stored.storage_folder == f"BATCH_A.{same_name_uid}"

    def test_a_batch_stored_alone_cannot_be_deleted_once_exported(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, _ = batches
        batch_service.set_as_storing_alone(first)
        set_status(stored_database_service, first, BatchStatus.EXPORTED)

        # Act
        with pytest.raises(NotAllowedActionError, match="in the outbox"):
            batch_service.set_as_deleting(first)


@pytest.mark.integration
class TestExportingAlone:
    @pytest.fixture()
    def stored_alone(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        batches: tuple[UUID, UUID],
    ) -> UUID:
        """Batch A, stored on its own."""
        first, _ = batches
        batch_service.set_as_storing_alone(first)
        set_status(stored_database_service, first, BatchStatus.COMPLETED)
        return first

    def add_image(
        self,
        database_service: DatabaseService,
        schema: ExampleSchema,
        dataset: Dataset,
        batch_uid: UUID,
        status: ImageStatus,
    ) -> None:
        with database_service.get_session() as session:
            slide = sample(
                session, dataset.uid, batch_uid, schema.slide_schema_uid, "slide"
            )
            image = DatabaseImage(
                dataset.uid,
                batch_uid,
                schema.image_schema_uid,
                "image",
                ImageFormat.DICOM_WSI,
                samples=slide,
            )
            image.status = status
            session.add(image)
            session.commit()

    def test_a_batch_stored_alone_is_exported_and_then_exported(
        self,
        batch_service: BatchService,
        stored_alone: UUID,
    ):
        # Act
        exporting = batch_service.set_as_exporting(stored_alone)
        exported = batch_service.set_as_exported(stored_alone)

        # Assert
        assert exporting.status == BatchStatus.EXPORTING
        assert exported.status == BatchStatus.EXPORTED

    def test_an_export_that_did_not_finish_is_reverted_with_why(
        self,
        batch_service: BatchService,
        stored_alone: UUID,
    ):
        # Arrange
        batch_service.set_as_exporting(stored_alone)

        # Act
        reverted = batch_service.revert_export(stored_alone, message="it broke")

        # Assert
        assert reverted.status == BatchStatus.COMPLETED
        assert reverted.status_message == "it broke"

    def test_a_batch_completed_with_the_project_is_not_exported_alone(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, _ = batches
        set_status(stored_database_service, first, BatchStatus.COMPLETED)

        # Act
        with pytest.raises(NotAllowedActionError, match="stored on its own"):
            batch_service.set_as_exporting(first)

    def test_a_batch_still_storing_is_not_exported(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        stored_alone: UUID,
    ):
        # Arrange
        set_status(stored_database_service, stored_alone, BatchStatus.IMAGE_STORING)

        # Act
        with pytest.raises(NotAllowedActionError, match="COMPLETED"):
            batch_service.set_as_exporting(stored_alone)

    def test_a_selected_image_not_stored_refuses_the_export(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        dataset: Dataset,
        stored_alone: UUID,
    ):
        # Arrange
        self.add_image(
            stored_database_service,
            schema,
            dataset,
            stored_alone,
            ImageStatus.POST_PROCESSED,
        )

        # Act
        with pytest.raises(NotAllowedActionError, match="1 selected .* not stored"):
            batch_service.set_as_exporting(stored_alone)

    def test_the_project_is_completed_once_every_batch_is_exported(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        project: Project,
        batches: tuple[UUID, UUID],
        stored_alone: UUID,
    ):
        """Exported counts as done for the project, as locked and completed do."""
        # Arrange
        _, second = batches
        with stored_database_service.get_session() as session:
            stored_database_service.delete_batch(session, second)
            session.commit()
        batch_service.set_as_exporting(stored_alone)

        # Act
        batch_service.set_as_exported(stored_alone)

        # Assert
        with stored_database_service.get_session() as session:
            assert (
                stored_database_service.get_project(session, project.uid).status
                == ProjectStatus.COMPLETED
            )

    def test_a_batch_stored_alone_refuses_the_export_of_the_project(
        self,
        project_service: ProjectService,
        stored_database_service: DatabaseService,
        project: Project,
        stored_alone: UUID,
    ):
        # Arrange
        with stored_database_service.get_session() as session:
            stored_database_service.get_project(
                session, project.uid
            ).status = ProjectStatus.COMPLETED
            session.commit()

        # Act
        with stored_database_service.get_session() as session:
            stored = stored_database_service.get_project(session, project.uid)
            with pytest.raises(NotAllowedActionError, match="stored on its own"):
                project_service.assert_can_export(stored, session)
