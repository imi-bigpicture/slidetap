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
from flask import Flask
from flask.testing import FlaskClient
from slidetap.database.project import DatabaseProject
from slidetap.external_interfaces import (
    MetadataExporter,
    MetadataImporter,
)
from slidetap.model import Project
from slidetap.service_provider import ServiceProvider
from slidetap.services import DatabaseService
from slidetap.web.controller.project_controller import ProjectController
from sqlalchemy import select
from tests.test_classes import (
    DummyLoginService,
)


@pytest.fixture()
def project_controller(
    app: Flask,
    service_provider: ServiceProvider,
    metadata_importer: MetadataImporter,
    metadata_exporter: MetadataExporter,
):

    project_controller = ProjectController(
        DummyLoginService(),
        service_provider.project_service,
        service_provider.validation_service,
        service_provider.batch_service,
        service_provider.dataset_service,
        service_provider.database_service,
        metadata_importer,
        metadata_exporter,
    )
    app.register_blueprint(project_controller.blueprint, url_prefix="/api/project")
    yield app


@pytest.fixture()
def test_client(project_controller: Flask):
    yield project_controller.test_client()


@pytest.mark.unittest
class TestSlideTapProjectController:
    def test_delete_project_not_found(self, test_client: FlaskClient):
        # Arrange

        # Act
        response = test_client.delete(f"api/project/{uuid4()}")

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
        response = test_client.delete(f"api/project/{project.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        with database_service.get_session() as session:
            deleted_database_project = session.scalar(
                select(DatabaseProject).where(DatabaseProject.uid == project.uid)
            )
            assert deleted_database_project is None
