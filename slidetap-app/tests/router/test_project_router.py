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


from http import HTTPStatus
from uuid import uuid4

import pytest
from decoy import Decoy
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from slidetap.database import DatabaseProject, NotAllowedActionError
from slidetap.model import Project, ProjectStatus
from slidetap.services import DatabaseService, ItemService
from slidetap.services.project_service import ProjectService
from slidetap.task import Scheduler
from slidetap.web.routers import project_router
from slidetap.web.services import MetadataExportService
from slidetap.web.services.login_service import LoginService


@pytest.fixture()
def login_service(decoy: Decoy):
    return decoy.mock(cls=LoginService)


@pytest.fixture()
def project_service(decoy: Decoy):
    return decoy.mock(cls=ProjectService)


@pytest.fixture()
def database_service(decoy: Decoy):
    return decoy.mock(cls=DatabaseService)


@pytest.fixture()
def item_service(decoy: Decoy):
    return decoy.mock(cls=ItemService)


@pytest.fixture()
def metadata_export_service(decoy: Decoy):
    return decoy.mock(cls=MetadataExportService)


@pytest.fixture()
def scheduler(decoy: Decoy):
    return decoy.mock(cls=Scheduler)


@pytest.fixture()
def project_router_app(
    simple_app: FastAPI,
    login_service: LoginService,
    project_service: ProjectService,
    database_service: DatabaseService,
    item_service: ItemService,
    metadata_export_service: MetadataExportService,
    scheduler: Scheduler,
):
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: project_service, provides=ProjectService)
    service_provider.provide(lambda: database_service, provides=DatabaseService)
    service_provider.provide(lambda: item_service, provides=ItemService)
    service_provider.provide(
        lambda: metadata_export_service, provides=MetadataExportService
    )
    service_provider.provide(lambda: scheduler, provides=Scheduler)

    container = make_async_container(service_provider)
    simple_app.include_router(project_router, tags=["project"])
    setup_dishka(container, simple_app)
    yield simple_app


@pytest.fixture()
def test_client(project_router_app: FastAPI):
    with TestClient(project_router_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapProjectRouter:
    def test_delete_project_not_found(
        self, decoy: Decoy, test_client: TestClient, project_service: ProjectService
    ):
        # Arrange
        uid = uuid4()
        decoy.when(project_service.get_optional(uid)).then_return(None)

        # Act
        response = test_client.delete(f"api/projects/project/{uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_project_being_exported_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        decoy.when(project_service.get_optional(project.uid)).then_return(project)
        decoy.when(project_service.set_as_deleting(project.uid)).then_raise(
            NotAllowedActionError("Cannot delete project while it is exporting")
        )

        # Act
        response = test_client.delete(f"api/projects/project/{project.uid}")

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT
        assert "exporting" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_project_is_scheduled(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        scheduler: Scheduler,
        project: Project,
    ):
        # Arrange
        deleting = project.model_copy(update={"status": ProjectStatus.DELETING})
        decoy.when(project_service.get_optional(project.uid)).then_return(project)
        decoy.when(project_service.set_as_deleting(project.uid)).then_return(deleting)

        # Act
        response = test_client.delete(f"api/projects/project/{project.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "scheduled"}
        decoy.verify(await scheduler.delete_project(deleting), times=1)

    def test_export_of_a_project_not_wholly_stored_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
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
        decoy.when(
            project_service.assert_can_export(database_project, session)
        ).then_raise(NotAllowedActionError("2 selected images are not stored"))

        # Act
        response = test_client.post(f"api/projects/project/{project.uid}/export")

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT
        assert "not stored" in response.json()["detail"]
