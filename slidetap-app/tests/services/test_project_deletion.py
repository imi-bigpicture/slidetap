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

"""What deleting a project leaves behind.

Against a real SQLite database rather than mocks: what is being pinned is which
rows the delete matches and what the ORM cascades do to them, neither of which
a mocked session says anything about.
"""

from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from slidetap_example import ExampleSchema
from sqlalchemy import func, select

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseItem,
    DatabaseSample,
)
from slidetap.model import BatchCreate, Dataset, ImageFormat, Project
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

UNKNOWN_SCHEMA_UID = UUID("f0f4a2c6-1d0e-4a5e-9a9f-0e7f2f1b6c31")
"""An item schema of a model revision the running application no longer loads."""


@pytest.fixture()
def schema_service(schema: ExampleSchema) -> SchemaService:
    return SchemaService(schema)


@pytest.fixture()
def storage_service(decoy: Decoy) -> StorageService:
    return decoy.mock(cls=StorageService)


@pytest.fixture()
def project_service(
    decoy: Decoy,
    schema_service: SchemaService,
    sqlite_database_service: DatabaseService,
    storage_service: StorageService,
) -> ProjectService:
    validation_service = ValidationService(schema_service, sqlite_database_service)
    return ProjectService(
        attribute_service=decoy.mock(cls=AttributeService),
        batch_service=decoy.mock(cls=BatchService),
        schema_service=schema_service,
        validation_service=validation_service,
        mapper_service=decoy.mock(cls=MapperService),
        database_service=sqlite_database_service,
        storage_service=storage_service,
    )


@pytest.fixture()
def batch_uid(
    sqlite_database_service: DatabaseService,
    dataset: Dataset,
    project: Project,
) -> UUID:
    """A project of one batch, stored, with nothing in the batch yet."""
    with sqlite_database_service.get_session() as session:
        sqlite_database_service.add_dataset(session, dataset)
        sqlite_database_service.add_project(session, project)
        batch = sqlite_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        )
        session.commit()
        return batch.uid


def items_left(database_service: DatabaseService) -> int:
    with database_service.get_session() as session:
        return session.scalar(select(func.count()).select_from(DatabaseItem)) or 0


@pytest.mark.unittest
class TestProjectDeletion:
    def test_item_of_a_schema_no_longer_loaded_is_deleted(
        self,
        project_service: ProjectService,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        dataset: Dataset,
        project: Project,
        batch_uid: UUID,
    ):
        """The batch is cleared out by what is in it, not by what is loaded.

        An item stored under a schema that a later model revision dropped is
        matched by nothing in ``schema_service.items``, and used to survive the
        delete and hold the batch down with it.
        """
        # Arrange
        assert UNKNOWN_SCHEMA_UID not in schema_service.items
        with sqlite_database_service.get_session() as session:
            session.add(
                DatabaseSample(
                    dataset.uid,
                    batch_uid,
                    schema_service.samples[next(iter(schema_service.samples))].uid,
                    "SLIDE-1",
                )
            )
            session.add(
                DatabaseSample(dataset.uid, batch_uid, UNKNOWN_SCHEMA_UID, "OLD-1")
            )
            session.commit()
        assert items_left(sqlite_database_service) == 2

        # Act
        deleted = project_service.delete(project.uid)

        # Assert
        assert deleted
        assert items_left(sqlite_database_service) == 0

    def test_an_annotation_goes_with_the_image_it_is_on(
        self,
        project_service: ProjectService,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        dataset: Dataset,
        project: Project,
        batch_uid: UUID,
    ):
        """Deleting is taken leaves first.

        ``annotation.image_uid`` is not nullable, so an image written out as
        deleted while the annotation on it is still there is rejected by the
        database. What decides it is the order the items are taken in, since a
        query partway through the loop flushes what has been marked so far.
        """
        # Arrange
        image_schema_uid = next(iter(schema_service.images))
        sample_schema_uid = next(iter(schema_service.samples))
        with sqlite_database_service.get_session() as session:
            sample = DatabaseSample(
                dataset.uid, batch_uid, sample_schema_uid, "SLIDE-1"
            )
            image = DatabaseImage(
                dataset.uid,
                batch_uid,
                image_schema_uid,
                "IMAGE-1",
                ImageFormat.DICOM_WSI,
                samples=sample,
            )
            session.add(sample)
            session.add(image)
            session.add(
                DatabaseAnnotation(
                    dataset.uid,
                    batch_uid,
                    uuid4(),
                    "ANNOTATION-1",
                    image=image,
                )
            )
            session.commit()
        assert items_left(sqlite_database_service) == 3

        # Act
        deleted = project_service.delete(project.uid)

        # Assert
        assert deleted
        assert items_left(sqlite_database_service) == 0
