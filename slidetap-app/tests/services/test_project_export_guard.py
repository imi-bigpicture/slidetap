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

"""What keeps a project that is not wholly in the outbox from being exported.

Against a real SQLite database: what is being pinned is which images the
guard counts, which a mocked session says nothing about.
"""

from uuid import UUID

import pytest
from decoy import Decoy
from slidetap_example import ExampleSchema

from slidetap.database import DatabaseImage, DatabaseSample, NotAllowedActionError
from slidetap.model import (
    BatchCreate,
    BatchStatus,
    Dataset,
    ImageFormat,
    ImageStatus,
    Project,
    ProjectStatus,
)
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    MapperService,
    ProjectService,
    SchemaService,
    StorageService,
    ValidationService,
)


@pytest.fixture()
def schema_service(schema: ExampleSchema) -> SchemaService:
    return SchemaService(schema)


@pytest.fixture()
def project_service(
    decoy: Decoy,
    schema_service: SchemaService,
    sqlite_database_service: DatabaseService,
) -> ProjectService:
    return ProjectService(
        attribute_service=decoy.mock(cls=AttributeService),
        batch_service=decoy.mock(cls=BatchService),
        schema_service=schema_service,
        validation_service=ValidationService(schema_service, sqlite_database_service),
        mapper_service=decoy.mock(cls=MapperService),
        database_service=sqlite_database_service,
        storage_service=decoy.mock(cls=StorageService),
    )


@pytest.fixture()
def batch_uid(
    sqlite_database_service: DatabaseService,
    dataset: Dataset,
    project: Project,
) -> UUID:
    """A completed project of one completed batch, ready to export."""
    with sqlite_database_service.get_session() as session:
        sqlite_database_service.add_dataset(session, dataset)
        stored = sqlite_database_service.add_project(session, project)
        stored.status = ProjectStatus.COMPLETED
        stored.valid_attributes = True
        batch = sqlite_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        )
        batch.status = BatchStatus.COMPLETED
        session.commit()
        return batch.uid


def add_image(
    database_service: DatabaseService,
    schema: ExampleSchema,
    dataset: Dataset,
    batch_uid: UUID,
    identifier: str,
    status: ImageStatus,
    selected: bool = True,
) -> None:
    with database_service.get_session() as session:
        slide = DatabaseSample(
            dataset.uid, batch_uid, schema.slide_schema_uid, f"slide-{identifier}"
        )
        image = DatabaseImage(
            dataset.uid,
            batch_uid,
            schema.image_schema_uid,
            identifier,
            ImageFormat.DICOM_WSI,
            samples=slide,
            selected=selected,
        )
        image.status = status
        session.add(slide)
        session.add(image)
        session.commit()


def assert_can_export(
    project_service: ProjectService,
    database_service: DatabaseService,
    project: Project,
) -> None:
    with database_service.get_session() as session:
        stored = database_service.get_project(session, project.uid)
        project_service.assert_can_export(stored, session)


@pytest.mark.integration
class TestExportGuard:
    def test_a_project_whose_images_are_all_stored_can_be_exported(
        self,
        project_service: ProjectService,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        dataset: Dataset,
        project: Project,
        batch_uid: UUID,
    ):
        add_image(
            sqlite_database_service, schema, dataset, batch_uid, "1", ImageStatus.STORED
        )

        assert_can_export(project_service, sqlite_database_service, project)

    def test_a_selected_image_never_stored_refuses_the_export(
        self,
        project_service: ProjectService,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        dataset: Dataset,
        project: Project,
        batch_uid: UUID,
    ):
        """What a batch delete that was interrupted once left behind: images
        selected, never processed, and about to be named in the bundle."""
        add_image(
            sqlite_database_service, schema, dataset, batch_uid, "1", ImageStatus.STORED
        )
        add_image(
            sqlite_database_service,
            schema,
            dataset,
            batch_uid,
            "2",
            ImageStatus.NOT_STARTED,
        )

        with pytest.raises(NotAllowedActionError, match="1 selected .* not stored"):
            assert_can_export(project_service, sqlite_database_service, project)

    def test_an_image_taken_out_of_the_project_is_not_counted(
        self,
        project_service: ProjectService,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        dataset: Dataset,
        project: Project,
        batch_uid: UUID,
    ):
        add_image(
            sqlite_database_service,
            schema,
            dataset,
            batch_uid,
            "1",
            ImageStatus.NOT_STARTED,
            selected=False,
        )

        assert_can_export(project_service, sqlite_database_service, project)

    def test_a_batch_being_deleted_refuses_the_export(
        self,
        project_service: ProjectService,
        sqlite_database_service: DatabaseService,
        project: Project,
        batch_uid: UUID,
    ):
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_batch(
                session, BatchCreate(name="going", project_uid=project.uid)
            ).status = BatchStatus.DELETING
            session.commit()

        with pytest.raises(NotAllowedActionError, match="being deleted"):
            assert_can_export(project_service, sqlite_database_service, project)

    def test_a_project_not_completed_refuses_the_export(
        self,
        project_service: ProjectService,
        sqlite_database_service: DatabaseService,
        project: Project,
        batch_uid: UUID,
    ):
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.get_project(
                session, project.uid
            ).status = ProjectStatus.IN_PROGRESS
            session.commit()

        with pytest.raises(NotAllowedActionError, match="COMPLETED"):
            assert_can_export(project_service, sqlite_database_service, project)
