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
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient as FlaskClient
from slidetap.apps.example.schema import ExampleSchema
from slidetap.config import Config, ConfigTest, DatabaseConfig, StorageConfig
from slidetap.database.project import DatabaseProject
from slidetap.model import Project
from slidetap.model.schema.root_schema import RootSchema
from slidetap.services import DatabaseService
from slidetap.services.attribute_service import AttributeService
from slidetap.services.batch_service import BatchService
from slidetap.services.mapper_service import MapperService
from slidetap.services.project_service import ProjectService
from slidetap.services.schema_service import SchemaService
from slidetap.services.storage_service import StorageService
from slidetap.services.validation_service import ValidationService
from slidetap.web.routers import project_router
from slidetap.web.services.auth.basic_auth_service import BasicAuthService
from slidetap.web.services.auth.hardcoded_basic_auth_service import (
    HardCodedBasicAuthTestService,
)
from slidetap.web.services.login_service import LoginService
from sqlalchemy import select
from tests.test_classes import (
    DummyLoginService,
)


@pytest.fixture()
def project_router_app(simple_app: FastAPI, config: ConfigTest):
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(
        lambda: HardCodedBasicAuthTestService({"username": "valid"}),
        provides=BasicAuthService,
    )
    service_provider.provide(DummyLoginService, provides=LoginService)
    service_provider.provide(lambda: config, provides=Config)
    service_provider.provide(BatchService)
    service_provider.provide(SchemaService)
    service_provider.provide(ValidationService)
    service_provider.provide(DatabaseService)
    service_provider.provide(ExampleSchema, provides=RootSchema)
    service_provider.provide(ProjectService)
    service_provider.provide(AttributeService)
    service_provider.provide(MapperService)
    service_provider.provide(StorageService)
    service_provider.provide(lambda: config.database_config, provides=DatabaseConfig)
    service_provider.provide(lambda: config.storage_config, provides=StorageConfig)

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
    def test_delete_project_not_found(self, test_client: FlaskClient):
        # Arrange

        # Act
        response = test_client.delete(f"api/projects/project/{uuid4()}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_project(
        self,
        test_client: FlaskClient,
        project: Project,
        database_service: DatabaseService,
    ):
        # Arrange
        with database_service.get_session() as session:
            database_project = database_service.add_project(session, project)
            project.uid = database_project.uid

        # Act
        response = test_client.delete(f"api/projects/project/{project.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        with database_service.get_session() as session:
            deleted_database_project = session.scalar(
                select(DatabaseProject).where(DatabaseProject.uid == project.uid)
            )
            assert deleted_database_project is None
