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
from fastapi.testclient import TestClient as FlaskClient
from slidetap.services.project_service import ProjectService
from slidetap.web.routers import project_router
from slidetap.web.services.login_service import LoginService


@pytest.fixture()
def login_service(decoy: Decoy):
    return decoy.mock(cls=LoginService)


@pytest.fixture()
def project_service(decoy: Decoy):
    return decoy.mock(cls=ProjectService)


@pytest.fixture()
def project_router_app(
    simple_app: FastAPI,
    login_service: LoginService,
    project_service: ProjectService,
):
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: project_service, provides=ProjectService)

    container = make_async_container(service_provider)
    simple_app.include_router(project_router, tags=["project"])
    setup_dishka(container, simple_app)
    yield simple_app


@pytest.fixture()
def test_client(project_router_app: FastAPI):
    with FlaskClient(project_router_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapProjectRouter:
    def test_delete_project_not_found(
        self, decoy: Decoy, test_client: FlaskClient, project_service: ProjectService
    ):
        # Arrange
        uid = uuid4()
        decoy.when(project_service.delete(uid)).then_return(None)

        # Act
        response = test_client.delete(f"api/projects/project/{uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_project_not_delete(
        self, decoy: Decoy, test_client: FlaskClient, project_service: ProjectService
    ):
        # Arrange
        uid = uuid4()
        decoy.when(project_service.delete(uid)).then_return(False)

        # Act
        response = test_client.delete(f"api/projects/project/{uid}")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_delete_project(
        self,
        decoy: Decoy,
        test_client: FlaskClient,
        project_service: ProjectService,
    ):
        # Arrange
        uid = uuid4()
        decoy.when(project_service.delete(uid)).then_return(True)

        # Act
        response = test_client.delete(f"api/projects/project/{uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
