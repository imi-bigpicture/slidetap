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
import json
from http import HTTPStatus
from uuid import uuid4

import pytest
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient as FlaskClient
from slidetap.config import Config, ConfigTest, DatabaseConfig, StorageConfig
from slidetap.database import DatabaseBatch
from slidetap.external_interfaces.metadata_import import MetadataImportInterface
from slidetap.model import Batch, BatchStatus, Dataset, Project
from slidetap.model.schema.root_schema import RootSchema
from slidetap.services import DatabaseService
from slidetap.services.batch_service import BatchService
from slidetap.services.schema_service import SchemaService
from slidetap.services.storage_service import StorageService
from slidetap.services.validation_service import ValidationService
from slidetap.task.scheduler import Scheduler
from slidetap.web.routers import batch_router
from slidetap.web.services.auth.basic_auth_service import BasicAuthService
from slidetap.web.services.auth.hardcoded_basic_auth_service import (
    HardCodedBasicAuthTestService,
)
from slidetap.web.services.image_import_service import ImageImportService
from slidetap.web.services.login_service import LoginService
from slidetap.web.services.metadata_import_service import MetadataImportService
from slidetap_example.interfaces.metadata_import import (
    ExampleImagePreProcessor,
    ExampleMetadataImportInterface,
)
from slidetap_example.schema import ExampleSchema
from sqlalchemy import select
from tests.test_classes import DummyLoginService


@pytest.fixture()
def batch_router_app(
    simple_app: FastAPI,
    config: ConfigTest,
):
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
    service_provider.provide(StorageService)
    service_provider.provide(ExampleSchema, provides=RootSchema)
    service_provider.provide(Scheduler)
    service_provider.provide(ImageImportService)
    service_provider.provide(MetadataImportService)
    service_provider.provide(
        ExampleMetadataImportInterface, provides=MetadataImportInterface
    )
    service_provider.provide(ExampleImagePreProcessor)
    service_provider.provide(lambda: config.database_config, provides=DatabaseConfig)
    service_provider.provide(lambda: config.storage_config, provides=StorageConfig)

    container = make_async_container(service_provider)
    simple_app.include_router(batch_router, tags=["batch"])
    setup_dishka(container, simple_app)
    yield simple_app


@pytest.fixture()
def test_client(batch_router_app: FastAPI):
    with FlaskClient(batch_router_app) as client:
        yield client


@pytest.fixture()
def empty_file():
    data = {}
    yield json.dumps(data).encode("utf-8")


@pytest.fixture()
def valid_file():
    data = {
        "observations": [
            {
                "name": "Observation-1",
                "identifier": "Observation-1",
                "case_identifier": "ABC",
                "diagnose": "Diagnosis-1",
                "report": "Report-1",
            }
        ],
        "patients": [
            {
                "name": "Patient-1",
                "identifier": "Patient-1",
                "sex": "F",
            }
        ],
        "cases": [
            {
                "name": "ABC",
                "identifier": "ABC",
                "patient_identifier": "Patient-1",
            }
        ],
        "specimens": [
            {
                "name": "1",
                "identifier": "ABC-1",
                "case_identifier": "ABC",
                "collection": "Excision",
                "fixation": "Neutral Buffered Formalin",
            },
            {
                "name": "2",
                "identifier": "ABC-2",
                "case_identifier": "ABC",
                "collection": "Excision",
                "fixation": "Neutral Buffered Formalin",
            },
        ],
        "blocks": [
            {
                "name": "A",
                "identifier": "ABC-1+2-A",
                "specimen_identifiers": ["ABC-1", "ABC-2"],
                "sampling": "Dissection",
                "embedding": "Paraffin wax",
            }
        ],
        "slides": [
            {
                "name": "1",
                "identifier": "ABC-1+2-A-1",
                "block_identifier": "ABC-1+2-A",
                "primary_stain": "hematoxylin",
                "secondary_stain": "water soluble eosin",
            },
            {
                "name": "2",
                "identifier": "ABC-1+2-A-2",
                "block_identifier": "ABC-1+2-A",
                "primary_stain": "hematoxylin",
                "secondary_stain": "water soluble eosin",
            },
        ],
        "images": [
            {
                "name": "1",
                "identifier": "ABC-1+2-A-1",
                "slide_identifier": "ABC-1+2-A-1",
            },
            {
                "name": "2",
                "identifier": "ABC-1+2-A-2",
                "slide_identifier": "ABC-1+2-A-2",
            },
        ],
    }
    yield json.dumps(data).encode("utf-8")


@pytest.fixture()
def non_valid_file():
    data = {"specimens_": [], "blocks_": [], "slides_": [], "images_": []}
    yield json.dumps(data).encode("utf-8")


@pytest.mark.unittest
class TestSlideTapBatchRouter:
    def test_delete_batch_not_found(self, test_client: FlaskClient):
        response = test_client.delete(f"api/batches/batch/{uuid4()}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_batch(
        self,
        test_client: FlaskClient,
        batch: Batch,
        project: Project,
        database_service: DatabaseService,
    ):
        with database_service.get_session() as session:
            database_project = database_service.add_project(session, project)
            database_batch = database_service.add_batch(session, batch)
            database_batch.project = database_project
            database_project.default_batch_uid = database_batch.uid
            batch.uid = database_batch.uid

        response = test_client.delete(f"api/batches/batch/{batch.uid}")
        assert response.status_code == HTTPStatus.OK
        with database_service.get_session() as session:
            deleted_database_batch = session.scalar(
                select(DatabaseBatch).where(DatabaseBatch.uid == batch.uid)
            )
            assert deleted_database_batch is None

    def test_upload_valid(
        self,
        test_client: FlaskClient,
        valid_file: bytes,
        batch: Batch,
        project: Project,
        dataset: Dataset,
        database_service: DatabaseService,
    ):
        # Arrange
        with database_service.get_session() as session:
            database_project = database_service.add_project(session, project)
            database_dataset = database_service.add_dataset(session, dataset)
            database_project.dataset = database_dataset
            database_batch = database_service.add_batch(session, batch)
            database_batch.project = database_project
            database_project.default_batch_uid = database_batch.uid
            batch.uid = database_batch.uid

        # Act
        response = test_client.post(
            f"api/batches/batch/{batch.uid}/uploadFile",
            files={
                "file": (
                    "test.json",
                    io.BytesIO(valid_file),
                    "application/json",
                )
            },
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        with database_service.get_session() as session:
            database_batch = session.query(DatabaseBatch).filter_by(uid=batch.uid).one()
            assert isinstance(database_batch, DatabaseBatch)
            assert database_batch.status == BatchStatus.METADATA_SEARCHING

    def test_upload_no_file(
        self,
        test_client: FlaskClient,
        batch: Batch,
        project: Project,
        dataset: Dataset,
        database_service: DatabaseService,
    ):
        with database_service.get_session() as session:
            database_project = database_service.add_project(session, project)
            database_dataset = database_service.add_dataset(session, dataset)
            database_project.dataset = database_dataset
            database_batch = database_service.add_batch(session, batch)
            database_batch.project = database_project
            database_project.default_batch_uid = database_batch.uid
            batch.uid = database_batch.uid

        response = test_client.post(
            f"api/batches/batch/{batch.uid}/uploadFile",
            data={},
            headers={"Content-Type": "multipart/form-data"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        with database_service.get_session() as session:
            database_batch = session.query(DatabaseBatch).filter_by(uid=batch.uid).one()
            assert isinstance(database_batch, DatabaseBatch)
            assert database_batch.status == BatchStatus.INITIALIZED

    def test_pre_process_valid(
        self,
        test_client: FlaskClient,
        batch: Batch,
        project: Project,
        dataset: Dataset,
        database_service: DatabaseService,
    ):
        with database_service.get_session() as session:
            database_project = database_service.add_project(session, project)
            database_dataset = database_service.add_dataset(session, dataset)
            database_project.dataset = database_dataset
            database_batch = database_service.add_batch(session, batch)
            database_batch.project = database_project
            database_project.default_batch_uid = database_batch.uid
            database_batch.status = BatchStatus.METADATA_SEARCH_COMPLETE
            batch.uid = database_batch.uid

        response = test_client.post(f"api/batches/batch/{batch.uid}/pre_process")
        assert response.status_code == HTTPStatus.OK
        with database_service.get_session() as session:
            database_batch = session.query(DatabaseBatch).filter_by(uid=batch.uid).one()
            assert isinstance(database_batch, DatabaseBatch)
            assert database_batch.status == BatchStatus.IMAGE_PRE_PROCESSING

    def test_pre_process_fail(self, test_client: FlaskClient):
        response = test_client.post(f"/api/batches/batch/{uuid4()}/pre_process")
        assert response.status_code == HTTPStatus.NOT_FOUND
