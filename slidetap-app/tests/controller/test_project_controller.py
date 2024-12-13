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

import io
from http import HTTPStatus
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pandas import DataFrame
from slidetap.database.project import DatabaseProject, ProjectStatus
from slidetap.services import ProcessingService, ProjectService, ValidationService
from slidetap.web.controller.project_controller import ProjectController
from slidetap.web.importer.fileparser import FileParser
from tests.test_classes import (
    DummyLoginService,
)
from werkzeug.datastructures import FileStorage


def df_to_bytes(df: DataFrame) -> bytes:
    with TemporaryDirectory() as folder:
        filename = folder + "/file.xlsx"
        df.to_excel(filename, index=False)

        with open(filename, "rb") as out:
            return out.read()


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


@pytest.fixture()
def empty_file():
    data = {"Case ID": [], "Block ID": [], "Stain": []}
    df = DataFrame(data)
    yield df_to_bytes(df)


@pytest.fixture()
def valid_file():
    data = {"Case ID": ["case 1"], "Block ID": ["block 1"], "Stain": ["stain 1"]}
    df = DataFrame(data)
    yield df_to_bytes(df)


@pytest.fixture()
def non_valid_file():
    data = {"Not Case ID": ["case 1"], "Block ID": ["block 1"], "Stain": ["stain 1"]}
    df = DataFrame(data)
    yield df_to_bytes(df)


@pytest.mark.unittest
class TestSlideTapProjectController:
    def test_status_project_not_found(self, test_client: FlaskClient):
        # Arrange

        # Act
        response = test_client.get(f"api/project/{uuid4()}/status")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_status_project(self, test_client: FlaskClient, project: DatabaseProject):
        # Arrange

        # Act
        response = test_client.get(f"api/project/{project.uid}/status")

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_delete_started_project(
        self, test_client: FlaskClient, project: DatabaseProject
    ):
        # Arrange
        project.status = ProjectStatus.IMAGE_PRE_PROCESSING

        # Act
        response = test_client.post(f"api/project/{project.uid}/delete")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_delete_project_not_found(self, test_client: FlaskClient):
        # Arrange

        # Act
        response = test_client.post(f"api/project/{uuid4()}/delete")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_not_started_project(
        self, test_client: FlaskClient, project: DatabaseProject
    ):
        # Arrange

        # Act
        response = test_client.post(f"api/project/{project.uid}/delete")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert DatabaseProject.get_optional(project.uid) is None

    def test_upload_valid(
        self, test_client: FlaskClient, project: DatabaseProject, valid_file: bytes
    ):
        # Arrange
        file = FileStorage(
            stream=io.BytesIO(valid_file),
            filename="test.xlsx",
            content_type=FileParser.CONTENT_TYPES["xlsx"],
        )
        form = {"name": "test", "file": file}

        # Act
        response = test_client.post(
            f"api/project/{project.uid}/uploadFile",
            data=form,
            content_type="multipart/form-data",
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert project.metadata_searching

    def test_upload_no_file(self, test_client: FlaskClient, project: DatabaseProject):
        # Arrange

        # Act
        response = test_client.post(
            f"api/project/{project.uid}/uploadFile",
            data={},
            content_type="multipart/form-data",
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert project.initialized

    # def test_upload_non_valid_extension(
    #     self, test_client: FlaskClient, project: Project, valid_file: bytes
    # ):
    #     # Arrange
    #     file = FileStorage(
    #         stream=io.BytesIO(valid_file),
    #         filename="test.not_xlsx",
    #         content_type=FileParser.CONTENT_TYPES["xlsx"],
    #     )
    #     form = {"name": "test", "file": file}

    #     # Act
    #     response = test_client.post(
    #         f"api/project/{project.uid}/uploadFile",
    #         data=form,
    #         content_type="multipart/form-data",
    #     )

    #     # Assert
    #     assert response.status_code == HTTPStatus.BAD_REQUEST

    # def test_upload_non_valid_content_type(
    #     self, test_client: FlaskClient, project: Project, valid_file: bytes
    # ):
    #     # Arrange
    #     file = FileStorage(
    #         stream=io.BytesIO(valid_file),
    #         filename="test.xlsx",
    #         content_type="not-ms-excel",
    #     )
    #     form = {"name": "test", "file": file}

    #     # Act
    #     response = test_client.post(
    #         f"api/project/{project.uid}/uploadFile",
    #         data=form,
    #         content_type="multipart/form-data",
    #     )

    #     # Assert
    #     assert response.status_code == HTTPStatus.BAD_REQUEST

    # def test_upload_non_valid_file(
    #     self, test_client: FlaskClient, project: Project, non_valid_file: bytes
    # ):
    #     # Arrange
    #     file = FileStorage(
    #         stream=io.BytesIO(non_valid_file),
    #         filename="test.xlsx",
    #         content_type=FileParser.CONTENT_TYPES["xlsx"],
    #     )
    #     form = {"name": "test", "file": file}

    #     # Act
    #     response = test_client.post(
    #         f"api/project/{project.uid}/uploadFile",
    #         data=form,
    #         content_type="multipart/form-data",
    #     )

    #     # Assert
    #     assert response.status_code == HTTPStatus.BAD_REQUEST

    # def test_upload_empty_file(
    #     self, test_client: FlaskClient, project: Project, empty_file: bytes
    # ):
    #     # Arrange
    #     file = FileStorage(
    #         stream=io.BytesIO(empty_file),
    #         filename="test.xlsx",
    #         content_type=FileParser.CONTENT_TYPES["xlsx"],
    #     )
    #     form = {"name": "test", "file": file}

    #     # Act
    #     response = test_client.post(
    #         f"api/project/{project.uid}/uploadFile",
    #         data=form,
    #         content_type="multipart/form-data",
    #     )

    #     # Assert
    #     assert response.status_code == HTTPStatus.OK

    def test_pre_process_valid(
        self, test_client: FlaskClient, project: DatabaseProject
    ):
        # Arrange
        project.status = ProjectStatus.METADATA_SEARCH_COMPLETE

        # Act
        response = test_client.post(f"api/project/{project.uid}/pre_process")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert project.image_pre_processing

    def test_pre_process_fail(self, test_client: FlaskClient):
        # Arrange

        # Act
        response = test_client.post(f"/api/project/{uuid4()}/pre_process")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
