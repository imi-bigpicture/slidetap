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
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple
from uuid import UUID

import pytest
from celery import Celery
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from slidetap.config import Config
from slidetap.model import BatchStatus, ImageStatus, ProjectStatus
from slidetap_example.config import (
    CeleryConfig,
    DatabaseConfig,
    DicomizationConfig,
    ExampleConfig,
    ImageCacheConfig,
)
from slidetap_example.schema import image_schema_uid, specimen_schema_uid
from slidetap_example.task_app_factory import make_celery
from slidetap_example.web_app_factory import create_app


class ExampleConfigTest(ExampleConfig):
    def __init__(self, tempdir: Path):
        self._storage_path = tempdir.joinpath("storage")
        self._keepalive = 30
        self._webapp_url = "http://localhost:13000"
        self._enforce_https = False
        self._log_level = "INFO"
        self._restore_projects = False
        self._dicomization_config = DicomizationConfig()
        self._celery_config = CeleryConfig(blocking=True)
        self._secret_key = "test"
        self._use_psuedonyms = False
        self._example_test_data_path = Path("tests/test_data")
        self._example_test_data_image_extension = ".svs"
        self._download_path = Path(tempdir).joinpath("download")
        self._web_app_log_level = "DEBUG"
        self._database_config = DatabaseConfig(f"sqlite:///{tempdir}/test.db", True)
        self._image_cache_config = ImageCacheConfig(10)


@pytest.fixture
def file():
    with open("tests/test_data/input.json", "rb") as input_file:
        yield ("input.json", input_file, "application/json")


@pytest.fixture
def celery_app(config: ExampleConfig):
    """Fixture to create a Celery app for testing."""

    return make_celery(config)


@pytest.fixture()
def config(tmpdir: str):
    return ExampleConfigTest(Path(tmpdir))


@pytest.fixture
def app(config: ExampleConfig, celery_app: Celery):
    app = create_app(config=config, celery_app=celery_app)
    yield app


@pytest.fixture
def test_client(app: FastAPI):
    yield TestClient(app)


@pytest.mark.integration
class TestIntegration:
    @pytest.mark.timeout(40)
    def test_integration(
        self, test_client: TestClient, file: Tuple[str, io.BytesIO, str], config: Config
    ):
        project_name = "integration project"
        # Login
        response = test_client.post(
            "/api/auth/login",
            json={"username": "test", "password": "test"},
        )
        assert response.status_code == HTTPStatus.OK
        csrf_token = response.cookies.get("csrf_token")
        access_token = response.cookies.get("access_token")
        assert csrf_token is not None and access_token is not None
        test_client.headers["X-CSRF-TOKEN"] = csrf_token
        test_client.cookies["csrf_token"] = csrf_token
        test_client.cookies["access_token"] = access_token

        # Get root schema:
        response = test_client.get("/api/schemas/root")
        root_schema = self.assert_status_ok_and_parse_dict_json(response)
        specimen_schema = root_schema["samples"][str(specimen_schema_uid)]
        collection_schema = specimen_schema["attributes"]["collection"]
        project_schema = root_schema["project"]
        submitter_schema = project_schema["attributes"]["submitter"]

        # Get mapping groups
        response = test_client.get("/api/mappers/groups")
        mapping_groups = self.assert_status_ok_and_parse_list_json(response)
        print(mapping_groups)

        # Create project
        response = test_client.post(
            "/api/projects/create",
            json={"name": project_name},
        )
        project = self.assert_status_ok_and_parse_dict_json(response)
        project_uid = project.get("uid", None)
        assert isinstance(project_uid, str)
        dataset_uid = project.get("datasetUid", None)
        assert isinstance(dataset_uid, str)

        # Update project
        project["name"] = project_name
        project["attributes"] = {
            "submitter": {
                "uid": str(UUID(int=0)),
                "schemaUid": submitter_schema["uid"],
                "updatedValue": "submitter",
                "attributeValueType": 1,
            }
        }
        response = test_client.post(
            f"/api/projects/project/{project_uid}",
            json=project,
        )
        project = self.assert_status_ok_and_parse_dict_json(response)
        assert project.get("name", None) == project_name

        # Get batches
        response = test_client.get(f"/api/batches?project_uid={project_uid}")
        batches = self.assert_status_ok_and_parse_list_json(response)
        assert len(batches) == 1
        batch = batches[0]
        batch_uid = batch.get("uid", None)
        assert isinstance(batch_uid, str)
        assert batch.get("projectUid", None) == project_uid

        # Upload batch file
        response = test_client.post(
            f"/api/batches/batch/{batch_uid}/uploadFile",
            files={"file": file},
        )
        assert response.status_code == HTTPStatus.OK

        # Get status
        self.wait_for_batch_status(
            test_client, batch_uid, BatchStatus.METADATA_SEARCH_COMPLETE
        )

        # Get specimens
        response = test_client.get(
            f"/api/items?datasetUid={dataset_uid}&itemSchemaUid={specimen_schema_uid}",
        )
        item_response = self.assert_status_ok_and_parse_dict_json(response)
        items = item_response["items"]
        assert len(items) == 2

        # Check specimen collection attributes
        for item in items:
            collection_attribute = next(
                attribute
                for attribute in item["attributes"].values()
                if attribute["schemaUid"] == collection_schema["uid"]
            )
            assert collection_attribute["displayValue"] == "Excision"

        # Check that collection schema attributes are mapped
        for item in items:
            collection_attribute = next(
                attribute
                for attribute in item["attributes"].values()
                if attribute["schemaUid"] == collection_schema["uid"]
            )
            response = test_client.get(
                f"/api/attributes/attribute/{collection_attribute['uid']}",
            )
            mapped_collection_attribute = self.assert_status_ok_and_parse_dict_json(
                response
            )
            assert mapped_collection_attribute["mappedValue"] is not None

        # Download
        response = test_client.post(
            f"/api/batches/batch/{batch_uid}/pre_process",
        )
        assert response.status_code == HTTPStatus.OK

        # Get status until completed or failed
        self.wait_for_batch_status(
            test_client, batch_uid, BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )

        # Get image status
        response = test_client.get(
            f"/api/items?datasetUid={dataset_uid}&itemSchemaUid={image_schema_uid}",
        )
        images_response = self.assert_status_ok_and_parse_dict_json(response)
        images = images_response["items"]
        assert len(images) == 2
        for image in images:
            assert isinstance(image, Mapping)
            assert image.get("status") == ImageStatus.PRE_PROCESSED.value

        # Process
        response = test_client.post(
            f"/api/batches/batch/{batch_uid}/process",
        )
        assert response.status_code == HTTPStatus.OK

        # Get status until completed or failed
        self.wait_for_batch_status(
            test_client, batch_uid, BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
        )

        # Get image status
        response = test_client.get(
            f"/api/items?datasetUid={dataset_uid}&itemSchemaUid={image_schema_uid}",
        )
        images_response = self.assert_status_ok_and_parse_dict_json(response)
        images = images_response["items"]
        assert len(images) == 2
        for image in images:
            assert isinstance(image, Mapping)
            assert image.get("status") == ImageStatus.POST_PROCESSED.value

        # Get thumbnails
        response = test_client.get(f"/api/images/thumbnails/{project_uid}")
        images_with_thumbnail = self.assert_status_ok_and_parse_list_json(response)

        for image in images_with_thumbnail:
            image_uid = image["uid"]
            response = test_client.get(f"/api/images/image/{image_uid}/thumbnail")
            assert response.status_code == HTTPStatus.OK

        # Get dzi and tile
        for image in images_with_thumbnail:
            image_uid = image["uid"]
            response = test_client.get(f"/api/images/image/{image_uid}")
            assert response.status_code == HTTPStatus.OK
            response = test_client.get(f"/api/images/image/{image_uid}/0/0_0.jpg")
            assert response.status_code == HTTPStatus.OK

        # Complete batch
        response = test_client.post(
            f"/api/batches/batch/{batch_uid}/complete",
        )
        assert response.status_code == HTTPStatus.OK
        # Get status until completed or failed
        self.wait_for_batch_status(test_client, batch_uid, BatchStatus.COMPLETED)

        # Export to storage
        response = test_client.post(
            f"/api/projects/project/{project_uid}/export",
        )
        assert response.status_code == HTTPStatus.OK

        # Get status until completed or failed
        self.wait_for_project_status(
            test_client, project_uid, ProjectStatus.EXPORT_COMPLETE
        )

        project_folder_name = f"{project_name}.{project_uid}"
        project_folder_path = config.storage_config.outbox.joinpath(project_folder_name)
        assert project_folder_path.exists()
        assert len(list(project_folder_path.iterdir())) == 3
        metadata_file = project_folder_path.joinpath("metadata", "metadata.json")
        assert metadata_file.exists()

        thumbnails_folder = project_folder_path.joinpath("thumbnails")
        assert thumbnails_folder.exists()

        images_folder = project_folder_path.joinpath("images")
        assert images_folder.exists()
        for image in images:
            assert isinstance(image, Mapping)
            image_path = images_folder.joinpath(image["identifier"])
            assert image_path.exists()
            thumbnail_path = thumbnails_folder.joinpath(
                image["identifier"]
            ).with_suffix(".jpeg")
            assert thumbnail_path.exists()

    @staticmethod
    def assert_status_ok_and_parse_dict_json(
        response: Response,
    ) -> Dict[str, Any]:
        assert response.status_code == HTTPStatus.OK
        parsed = response.json()
        assert isinstance(parsed, dict)
        return parsed

    @staticmethod
    def assert_status_ok_and_parse_list_json(
        response: Response,
    ) -> List[Dict[str, Any]]:
        assert response.status_code == HTTPStatus.OK
        parsed = response.json()
        assert isinstance(parsed, list)
        return parsed

    @classmethod
    def wait_for_batch_status(
        cls, test_client: TestClient, batch_uid: str, expected_status: BatchStatus
    ):
        status = cls.get_batch_status(test_client, batch_uid)
        while status != expected_status and status != BatchStatus.FAILED:
            time.sleep(1)
            status = cls.get_batch_status(test_client, batch_uid)

        assert status == expected_status

    @classmethod
    def wait_for_project_status(
        cls, test_client: TestClient, project_uid: str, expected_status: ProjectStatus
    ):
        status = cls.get_project_status(test_client, project_uid)
        while status != expected_status and status != ProjectStatus.FAILED:
            time.sleep(1)
            status = cls.get_project_status(test_client, project_uid)

        assert status == expected_status

    @staticmethod
    def get_status(test_client: TestClient, endpoint: str, uid: str):
        response = test_client.get(f"/api/{endpoint}/{uid}")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data is not None
        assert isinstance(data, Mapping)
        assert data.get("uid", None) == uid
        return data.get("status", None)

    @classmethod
    def get_batch_status(cls, test_client: TestClient, uid: str):
        status = cls.get_status(test_client, "batches/batch", uid)
        assert isinstance(status, int)
        return BatchStatus(status)

    @classmethod
    def get_project_status(cls, test_client: TestClient, uid: str):
        status = cls.get_status(test_client, "projects/project", uid)
        assert isinstance(status, int)
        return ProjectStatus(status)
