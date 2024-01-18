import io
from http import HTTPStatus
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pandas import DataFrame
from werkzeug.datastructures import FileStorage

from slidetap.controller.project_controller import ProjectController
from slidetap.database.project import Project, ProjectStatus
from slidetap.importer.metadata import FileParser
from slidetap.services import ProjectService
from slidetap.storage.storage import Storage
from slidetap.test_classes import (
    DummyImageExporter,
    DummyImageImporter,
    DummyMetadataImporter,
    LoginTestService,
)
from slidetap.test_classes.metadata_exporter import DummyMetadataExporter
from slidetap.test_classes.storage import TempStorage


def df_to_bytes(df: DataFrame) -> bytes:
    with TemporaryDirectory() as folder:
        filename = folder + "/file.xlsx"
        df.to_excel(filename, index=False)

        with open(filename, "rb") as out:
            return out.read()


@pytest.fixture()
def storage():
    storage = TempStorage()
    yield storage
    storage.cleanup()


@pytest.fixture()
def project_controller(app: Flask, storage: Storage):
    project_service = ProjectService(
        DummyImageImporter(),
        DummyImageExporter(storage),
        DummyMetadataImporter(),
        DummyMetadataExporter(storage),
    )
    project_controller = ProjectController(LoginTestService(), project_service)
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

    def test_status_project(self, test_client: FlaskClient, project: Project):
        # Arrange

        # Act
        response = test_client.get(f"api/project/{project.uid}/status")

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_delete_started_project(self, test_client: FlaskClient, project: Project):
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
        self, test_client: FlaskClient, project: Project
    ):
        # Arrange

        # Act
        response = test_client.post(f"api/project/{project.uid}/delete")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert Project.get(project.uid) is None

    def test_upload_valid(
        self, test_client: FlaskClient, project: Project, valid_file: bytes
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

    def test_upload_no_file(self, test_client: FlaskClient, project: Project):
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

    def test_download_valid(self, test_client: FlaskClient, project: Project):
        # Arrange
        project.status = ProjectStatus.METADATA_SEARCH_COMPLETE

        # Act
        response = test_client.post(f"api/project/{project.uid}/download")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert project.image_pre_processing

    def test_start_fail(self, test_client: FlaskClient):
        # Arrange

        # Act
        response = test_client.post(f"/api/project/{uuid4()}/start")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
