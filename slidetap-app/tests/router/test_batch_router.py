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
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slidetap.model import Batch, BatchStatus
from slidetap.services import BatchService
from slidetap.web.routers import batch_router
from slidetap.web.services import (
    ImageImportService,
    LoginService,
    MetadataImportService,
)


@pytest.fixture()
def login_service(decoy: Decoy):
    return decoy.mock(cls=LoginService)


@pytest.fixture()
def batch_service(decoy: Decoy):
    return decoy.mock(cls=BatchService)


@pytest.fixture()
def image_import_service(decoy: Decoy):
    return decoy.mock(cls=ImageImportService)


@pytest.fixture()
def metadata_import_service(decoy: Decoy):
    return decoy.mock(cls=MetadataImportService)


@pytest.fixture()
def batch_router_app(
    simple_app: FastAPI,
    login_service: LoginService,
    batch_service: BatchService,
    image_import_service: ImageImportService,
    metadata_import_service: MetadataImportService,
):
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: batch_service, provides=BatchService)
    service_provider.provide(lambda: image_import_service, provides=ImageImportService)
    service_provider.provide(
        lambda: metadata_import_service, provides=MetadataImportService
    )

    container = make_async_container(service_provider)
    simple_app.include_router(batch_router, tags=["batch"])
    setup_dishka(container, simple_app)
    yield simple_app


@pytest.fixture()
def test_client(batch_router_app: FastAPI):
    with TestClient(batch_router_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapBatchRouter:
    def test_delete_batch_not_found(self, test_client: TestClient):
        response = test_client.delete(f"api/batches/batch/{uuid4()}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_batch(
        self,
        decoy: Decoy,
        test_client: TestClient,
        batch: Batch,
        batch_service: BatchService,
    ):
        # Arrange
        def set_status_deleted():
            batch.status = BatchStatus.DELETED
            return batch

        decoy.when(batch_service.delete(batch.uid)).then_return(set_status_deleted())

        # Act
        response = test_client.delete(f"api/batches/batch/{batch.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_upload_valid(
        self,
        decoy: Decoy,
        test_client: TestClient,
        batch: Batch,
        metadata_import_service: MetadataImportService,
    ):
        # Arrange
        decoy.when(metadata_import_service.search(batch.uid, Anything())).then_return(
            batch
        )

        # Act
        response = test_client.post(
            f"api/batches/batch/{batch.uid}/uploadFile",
            files={
                "file": (
                    "test.json",
                    io.BytesIO(),
                    "application/json",
                )
            },
        )

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_upload_no_file(
        self,
        test_client: TestClient,
        batch: Batch,
    ):
        # Arrange

        # Act
        response = test_client.post(
            f"api/batches/batch/{batch.uid}/uploadFile",
            data={},
            headers={"Content-Type": "multipart/form-data"},
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_pre_process_valid(
        self,
        decoy: Decoy,
        test_client: TestClient,
        batch: Batch,
        image_import_service: ImageImportService,
    ):
        # Arrange
        decoy.when(image_import_service.pre_process_batch(batch.uid)).then_return(batch)

        # Act
        response = test_client.post(f"api/batches/batch/{batch.uid}/pre_process")

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_pre_process_fail(
        self,
        decoy: Decoy,
        test_client: TestClient,
        image_import_service: ImageImportService,
    ):
        # Arrange
        uid = uuid4()
        decoy.when(image_import_service.pre_process_batch(uid)).then_return(None)

        # Act
        response = test_client.post(f"/api/batches/batch/{uid}/pre_process")
        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
