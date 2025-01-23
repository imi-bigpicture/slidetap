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
from slidetap.database import DatabaseBatch, DatabaseProject, db
from slidetap.importer.fileparser import FileParser
from slidetap.model import Batch, BatchStatus
from slidetap.services.batch_service import BatchService
from slidetap.services.validation_service import ValidationService
from slidetap.web.controller.batch_controller import BatchController
from slidetap.web.processing_service import ProcessingService
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
def batch_controller(
    app: Flask,
    batch_service: BatchService,
    validation_service: ValidationService,
    processing_service: ProcessingService,
):

    batch_controller = BatchController(
        DummyLoginService(),
        batch_service,
        processing_service,
        validation_service,
    )
    app.register_blueprint(batch_controller.blueprint, url_prefix="/api/batch")
    yield app


@pytest.fixture()
def test_client(batch_controller: Flask):
    yield batch_controller.test_client()


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
class TestSlideTapBatchController:
    def test_delete_batch_not_found(self, test_client: FlaskClient):
        # Arrange

        # Act
        response = test_client.delete(f"api/batch/{uuid4()}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_batch(
        self, test_client: FlaskClient, database_batch: DatabaseBatch
    ):
        # Arrange

        # Act
        response = test_client.delete(f"api/batch/{database_batch.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        deleted_database_batch = (
            db.session.query(DatabaseBatch).filter_by(uid=database_batch.uid).one()
        )
        assert deleted_database_batch is None

    def test_upload_valid(
        self,
        test_client: FlaskClient,
        database_batch: DatabaseBatch,
        valid_file: bytes,
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
            f"api/batch/{database_batch.uid}/uploadFile",
            data=form,
            content_type="multipart/form-data",
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        database_batch = (
            db.session.query(DatabaseBatch).filter_by(uid=database_batch.uid).one()
        )
        assert isinstance(database_batch, DatabaseBatch)
        assert database_batch.status == BatchStatus.METADATA_SEARCHING

    def test_upload_no_file(
        self,
        test_client: FlaskClient,
        batch: Batch,
    ):
        # Arrange
        database_batch = DatabaseBatch.get_or_create_from_model(batch)
        # Arrange

        # Act
        response = test_client.post(
            f"api/batch/{database_batch.uid}/uploadFile",
            data={},
            content_type="multipart/form-data",
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        database_batch = (
            db.session.query(DatabaseBatch).filter_by(uid=database_batch.uid).one()
        )
        assert isinstance(database_batch, DatabaseBatch)
        assert database_batch.status == BatchStatus.INITIALIZED

    # def test_upload_non_valid_extension(
    #     self, test_client: FlaskClient, batch: Project, valid_file: bytes
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
    #         f"api/batch/{batch.uid}/uploadFile",
    #         data=form,
    #         content_type="multipart/form-data",
    #     )

    #     # Assert
    #     assert response.status_code == HTTPStatus.BAD_REQUEST

    # def test_upload_non_valid_content_type(
    #     self, test_client: FlaskClient, batch: Project, valid_file: bytes
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
    #         f"api/batch/{batch.uid}/uploadFile",
    #         data=form,
    #         content_type="multipart/form-data",
    #     )

    #     # Assert
    #     assert response.status_code == HTTPStatus.BAD_REQUEST

    # def test_upload_non_valid_file(
    #     self, test_client: FlaskClient, batch: Project, non_valid_file: bytes
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
    #         f"api/batch/{batch.uid}/uploadFile",
    #         data=form,
    #         content_type="multipart/form-data",
    #     )

    #     # Assert
    #     assert response.status_code == HTTPStatus.BAD_REQUEST

    # def test_upload_empty_file(
    #     self, test_client: FlaskClient, batch: Project, empty_file: bytes
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
    #         f"api/batch/{batch.uid}/uploadFile",
    #         data=form,
    #         content_type="multipart/form-data",
    #     )

    #     # Assert
    #     assert response.status_code == HTTPStatus.OK

    def test_pre_process_valid(
        self, test_client: FlaskClient, database_batch: DatabaseBatch
    ):
        # Arrange
        database_batch.status = BatchStatus.METADATA_SEARCH_COMPLETE

        # Act
        response = test_client.post(f"api/batch/{database_batch.uid}/pre_process")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert database_batch.status == BatchStatus.IMAGE_PRE_PROCESSING

    def test_pre_process_fail(self, test_client: FlaskClient):
        # Arrange

        # Act
        response = test_client.post(f"/api/batch/{uuid4()}/pre_process")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
