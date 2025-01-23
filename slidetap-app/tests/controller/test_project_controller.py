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
from slidetap.services.project_service import ProjectService
from slidetap.services.validation_service import ValidationService
from slidetap.web.controller.project_controller import ProjectController
from slidetap.web.processing_service import ProcessingService
from tests.test_classes import (
    DummyLoginService,
)


@pytest.fixture()
def project_controller(
    app: Flask,
    project_service: ProjectService,
    validation_service: ValidationService,
    processing_service: ProcessingService,
):

    project_controller = ProjectController(
        DummyLoginService(), project_service, validation_service, processing_service
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
        self, test_client: FlaskClient, database_project: DatabaseProject
    ):
        # Arrange

        # Act
        response = test_client.delete(f"api/project/{database_project.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        deleted_database_project = DatabaseProject.query.get(database_project.uid)
        assert deleted_database_project is None
