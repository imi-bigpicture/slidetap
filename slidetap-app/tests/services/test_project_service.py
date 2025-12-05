#    Copyright 2024 SECTRA AB
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


import pytest
from decoy import Decoy
from slidetap.database import DatabaseBatch, DatabaseProject
from slidetap.model import ItemSchema, Project
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
from sqlalchemy.orm import Session


@pytest.fixture()
def database_service(decoy: Decoy) -> DatabaseService:
    return decoy.mock(cls=DatabaseService)


@pytest.fixture()
def attribute_service(decoy: Decoy) -> AttributeService:
    return decoy.mock(cls=AttributeService)


@pytest.fixture()
def batch_service(decoy: Decoy) -> BatchService:
    return decoy.mock(cls=BatchService)


@pytest.fixture()
def schema_service(decoy: Decoy) -> SchemaService:
    return decoy.mock(cls=SchemaService)


@pytest.fixture()
def validation_service(decoy: Decoy) -> ValidationService:
    return decoy.mock(cls=ValidationService)


@pytest.fixture()
def mapper_service(decoy: Decoy) -> MapperService:
    return decoy.mock(cls=MapperService)


@pytest.fixture()
def storage_service(decoy: Decoy) -> StorageService:
    return decoy.mock(cls=StorageService)


@pytest.fixture()
def project_service(
    database_service: DatabaseService,
    attribute_service: AttributeService,
    batch_service: BatchService,
    schema_service: SchemaService,
    validation_service: ValidationService,
    mapper_service: MapperService,
    storage_service: StorageService,
) -> ProjectService:
    return ProjectService(
        attribute_service=attribute_service,
        batch_service=batch_service,
        schema_service=schema_service,
        validation_service=validation_service,
        mapper_service=mapper_service,
        database_service=database_service,
        storage_service=storage_service,
    )


@pytest.mark.unittest
class TestProjectService:
    def test_get_project(
        self,
        decoy: Decoy,
        project_service: ProjectService,
        database_service: DatabaseService,
        project: Project,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        database_project = decoy.mock(cls=DatabaseProject)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(database_service.get_project(session, project.uid)).then_return(
            database_project
        )
        decoy.when(database_project.model).then_return(project)

        # Act
        result = project_service.get(project.uid)

        # Assert
        assert result == project

    def test_delete_project(
        self,
        decoy: Decoy,
        project_service: ProjectService,
        database_service: DatabaseService,
        schema_service: SchemaService,
        storage_service: StorageService,
        project: Project,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        database_project = decoy.mock(cls=DatabaseProject)
        batch = decoy.mock(cls=DatabaseBatch)
        item_schema = decoy.mock(cls=ItemSchema)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(
            database_service.get_optional_project(session, project.uid)
        ).then_return(database_project)
        decoy.when(database_project.batches).then_return(set([batch]))
        decoy.when(database_project.model).then_return(project)
        decoy.when(schema_service.items).then_return({item_schema.uid: item_schema})

        # Act
        deleted = project_service.delete(project.uid)

        # Assert
        assert deleted
        decoy.verify(
            database_service.delete_items(session, item_schema, batch), times=1
        )
        decoy.verify(session.delete(batch), times=1)
        decoy.verify(session.delete(database_project), times=1)
        decoy.verify(storage_service.cleanup_project(project), times=1)
