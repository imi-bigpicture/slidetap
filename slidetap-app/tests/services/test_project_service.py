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


from uuid import uuid4

import pytest
from decoy import Decoy, matchers
from sqlalchemy import ScalarResult
from sqlalchemy.orm import Session

from slidetap.database import DatabaseProject
from slidetap.model import (
    NotAllowedActionError,
    Project,
    ProjectStatus,
    SeedClearedError,
)
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    MapperService,
    MigrationService,
    ProjectService,
    SchemaService,
    StorageService,
    ValidationService,
)


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
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.can_change(matchers.Anything())).then_return(True)
    decoy.when(
        schema_service.can_change(matchers.Anything(), matchers.Anything())
    ).then_return(True)
    return schema_service


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
    decoy: Decoy,
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
        migration_service=decoy.mock(cls=MigrationService),
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

    @pytest.mark.parametrize("completed", [True, False])
    def test_get_completed(
        self,
        decoy: Decoy,
        project_service: ProjectService,
        database_service: DatabaseService,
        project: Project,
        completed: bool,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        database_project = decoy.mock(cls=DatabaseProject)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(database_service.get_project(session, project.uid)).then_return(
            database_project
        )
        decoy.when(database_project.completed).then_return(completed)
        decoy.when(database_project.model).then_return(project)

        # Act
        result = project_service.get_completed(project.uid)

        # Assert
        assert result == (project if completed else None)

    def test_get_exportable_refuses_a_project_that_is_not_completed(
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
        decoy.when(database_project.completed).then_return(False)
        decoy.when(database_project.status).then_return(ProjectStatus.IN_PROGRESS)

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="COMPLETED"):
            project_service.get_exportable(project.uid)

    @pytest.mark.parametrize(
        ["completed", "export_complete", "failed", "settled"],
        [
            (True, False, False, True),
            (False, True, False, True),
            (False, False, True, True),
            (False, False, False, False),
        ],
    )
    def test_get_settled(
        self,
        decoy: Decoy,
        project_service: ProjectService,
        database_service: DatabaseService,
        project: Project,
        completed: bool,
        export_complete: bool,
        failed: bool,
        settled: bool,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        database_project = decoy.mock(cls=DatabaseProject)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(database_service.get_project(session, project.uid)).then_return(
            database_project
        )
        decoy.when(database_project.completed).then_return(completed)
        decoy.when(database_project.export_complete).then_return(export_complete)
        decoy.when(database_project.failed).then_return(failed)
        decoy.when(database_project.status).then_return(ProjectStatus.IN_PROGRESS)
        decoy.when(database_project.model).then_return(project)

        # Act & Assert
        if settled:
            assert project_service.get_settled(project.uid) == project
        else:
            with pytest.raises(NotAllowedActionError, match="completed, exported"):
                project_service.get_settled(project.uid)

    def test_get_seed(
        self,
        decoy: Decoy,
        project_service: ProjectService,
        database_service: DatabaseService,
        project: Project,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        database_project = decoy.mock(cls=DatabaseProject)
        seed = uuid4()
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(database_service.get_project(session, project.uid)).then_return(
            database_project
        )
        decoy.when(database_project.seed).then_return(seed)

        # Act
        result = project_service.get_seed(project.uid)

        # Assert
        assert result == seed

    def test_get_export_seed(
        self,
        decoy: Decoy,
        project_service: ProjectService,
        database_service: DatabaseService,
        project: Project,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        result = decoy.mock(cls=ScalarResult[DatabaseProject])
        database_project = decoy.mock(cls=DatabaseProject)
        seed = uuid4()
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(session.scalars(matchers.Anything())).then_return(result)
        decoy.when(result.one()).then_return(database_project)
        decoy.when(database_project.seed).then_return(seed)

        # Act
        export_seed = project_service.get_export_seed(project.dataset_uid)

        # Assert
        assert export_seed == seed

    def test_get_export_seed_is_refused_once_the_seed_is_cleared(
        self,
        decoy: Decoy,
        project_service: ProjectService,
        database_service: DatabaseService,
        project: Project,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        result = decoy.mock(cls=ScalarResult[DatabaseProject])
        database_project = decoy.mock(cls=DatabaseProject)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(session.scalars(matchers.Anything())).then_return(result)
        decoy.when(result.one()).then_return(database_project)
        decoy.when(database_project.seed).then_return(None)
        decoy.when(database_project.uid).then_return(project.uid)

        # Act & Assert
        with pytest.raises(SeedClearedError):
            project_service.get_export_seed(project.dataset_uid)

    def test_clear_seed(
        self,
        decoy: Decoy,
        project_service: ProjectService,
        database_service: DatabaseService,
        project: Project,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        database_project = decoy.mock(cls=DatabaseProject)
        decoy.when(database_service.get_session(None)).then_enter_with(session)
        decoy.when(database_service.get_project(session, project.uid)).then_return(
            database_project
        )
        decoy.when(database_project.uid).then_return(project.uid)
        decoy.when(database_project.model).then_return(project)

        # Act
        result = project_service.clear_seed(project.uid)

        # Assert
        assert result == project
        assert database_project.seed is None
