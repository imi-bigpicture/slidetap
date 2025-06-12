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

import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import Any, Dict, List, Mapping
from uuid import UUID, uuid4

import py
import pytest
from celery import Celery
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from slidetap.apps.example.config import ExampleConfig
from slidetap.apps.example.mapper_injector import ExampleMapperInjector
from slidetap.apps.example.schema import ExampleSchema
from slidetap.apps.example.task_app_factory import make_celery
from slidetap.apps.example.web_app_factory import create_app
from slidetap.config import Config
from slidetap.model import (
    AttributeValueType,
    BatchStatus,
    ImageStatus,
    ProjectStatus,
)
from slidetap.services.mapper_service import MapperInjector, MapperService


@pytest.fixture
def file():
    with open("tests/test_data/input.json", "rb") as input_file:
        yield ("input.json", input_file, "application/json")


@pytest.fixture
def celery_app(config: ExampleConfig):
    """Fixture to create a Celery app for testing."""

    return make_celery(config)


@pytest.fixture
def app(config: ExampleConfig, celery_app: Celery, mapper_injector: MapperInjector):
    app = create_app(config=config, celery_app=celery_app)
    # mapper_injector.inject()
    yield app


@pytest.fixture
def test_client(app: FastAPI):
    yield TestClient(app)


def get_status(test_client: TestClient, endpoint: str, uid: str):
    response = test_client.get(f"/api/{endpoint}/{uid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data is not None
    assert isinstance(data, Mapping)
    assert data.get("uid", None) == uid
    return data.get("status", None)


def get_batch_status(test_client: TestClient, uid: str):
    status = get_status(test_client, "batches/batch", uid)
    assert isinstance(status, int)
    return BatchStatus(status)


def get_project_status(test_client: TestClient, uid: str):
    status = get_status(test_client, "projects/project", uid)
    assert isinstance(status, int)
    return ProjectStatus(status)


@pytest.mark.integration
class TestIntegration:
    @pytest.mark.timeout(40)
    def test_integration(self, test_client: TestClient, file, config: Config):
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
        specimen_schema_uid = "c78d0dcf-1723-4729-8c05-d438a184c6b4"
        image_schema_uid = "f537cbcc-8d71-4874-a900-3e6d2a377728"
        response = test_client.get("/api/schemas/root")
        root_schema = self.assert_status_ok_and_parse_dict_json(response)
        specimen_schema = root_schema["samples"][specimen_schema_uid]
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
        print(f"Wating for batch {batch_uid} to be created")
        self.wait_for_batch_status(
            test_client, batch_uid, BatchStatus.METADATA_SEARCH_COMPLETE
        )
        print("Batch created")

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

        # # Get attributes for collection schema
        # response = test_client.get(
        #     f"/api/attributes/attributeschema/{collection_schema['uid']}",
        #
        # )
        # attributes = self.assert_status_ok_and_parse_list_json(response)
        # collection_attribute = next(
        #     (
        #         attribute
        #         for attribute in attributes
        #         if attribute["schemaUid"] == collection_schema["uid"]
        #     ),
        #     None,
        # )
        # assert collection_attribute is not None
        # assert collection_attribute["mappingStatus"] == ValueStatus.NOT_MAPPED.value
        # assert collection_attribute["displayValue"] == "Excision"

        # Add mapper for collection schema attributes
        response = test_client.post(
            "/api/mappers/create",
            json={
                "uid": str(UUID(int=0)),
                "name": "collection",
                "attributeSchemaUid": collection_schema["uid"],
                "root_attribute_schema_uid": collection_schema["uid"],
            },
        )
        mapper = self.assert_status_ok_and_parse_dict_json(response)

        # Add mapper group
        response = test_client.post(
            "/api/mappers/groups/create",
            json={
                "uid": str(UUID(int=0)),
                "name": "Collection Mapper Group",
                "mappers": [mapper["uid"]],
                "defaultEnabled": True,
            },
        )
        mapper_group = self.assert_status_ok_and_parse_dict_json(response)

        # Update project with mapper group
        project["mapperGroups"] = [mapper_group["uid"]]
        response = test_client.post(
            f"/api/projects/project/{project_uid}",
            json=project,
        )
        project = self.assert_status_ok_and_parse_dict_json(response)
        assert project.get("mapperGroups", None) == [mapper_group["uid"]]

        # Add mapping for collection schema attributes
        mapped_value = {
            "meaning": "Excision",
            "scheme": "CUSTOM",
            "schemeVersion": None,
            "code": "Excision",
        }
        expression = "Excision"
        response = test_client.post(
            "/api/mappers/mappings/create",
            json={
                "uid": str(UUID(int=0)),
                "expression": expression,
                "attribute": {
                    "originalValue": mapped_value,
                    "schemaUid": collection_schema["uid"],
                    "uid": str(UUID(int=0)),
                    "mappedValue": None,
                    "updatedValue": None,
                    "mappableValue": None,
                    "attributeValueType": AttributeValueType.CODE.value,
                },
                "mapperUid": mapper["uid"],
            },
        )
        mapping_item = self.assert_status_ok_and_parse_dict_json(response)

        assert mapping_item["uid"] is not None
        assert mapping_item["expression"] == expression
        assert mapping_item["attribute"]["originalValue"] == mapped_value

        # Check that collection schema attributes are now mapped
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
            assert mapped_collection_attribute["mappedValue"] == mapped_value

        # Update mapping item for collection schema attributes
        updated_mapped_value = {
            "meaning": "Excision 2",
            "scheme": "CUSTOM 2",
            "schemeVersion": None,
            "code": "Excision 2",
        }
        response = test_client.post(
            f"/api/mappers/mappings/mapping/{mapping_item['uid']}",
            json={
                "uid": mapping_item["uid"],
                "expression": expression,
                "attribute": {
                    "originalValue": updated_mapped_value,
                    "updatedValue": None,
                    "mappedValue": None,
                    "schemaUid": collection_schema["uid"],
                    "uid": str(UUID(int=0)),
                    "mappableValue": None,
                    "attributeValueType": AttributeValueType.CODE.value,
                },
                "mapperUid": mapper["uid"],
            },
        )
        updated_mapping_item = self.assert_status_ok_and_parse_dict_json(response)

        assert updated_mapping_item["uid"] == mapping_item["uid"]
        assert updated_mapping_item["expression"] == expression
        assert (
            updated_mapping_item["attribute"]["originalValue"] == updated_mapped_value
        )

        # Check that attributes are now mapped to updated value
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
            assert mapped_collection_attribute["mappedValue"] == updated_mapped_value

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
        wsi_schema_uid = "f537cbcc-8d71-4874-a900-3e6d2a377728"
        response = test_client.get(
            f"/api/items?datasetUid={dataset_uid}&itemSchemaUid={wsi_schema_uid}",
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

    @staticmethod
    def wait_for_batch_status(
        test_client: TestClient, batch_uid: str, expected_status: BatchStatus
    ):
        status = get_batch_status(test_client, batch_uid)
        while status != expected_status and status != BatchStatus.FAILED:
            time.sleep(1)
            status = get_batch_status(test_client, batch_uid)

        assert status == expected_status

    @staticmethod
    def wait_for_project_status(
        test_client: TestClient, project_uid: str, expected_status: ProjectStatus
    ):
        status = get_project_status(test_client, project_uid)
        while status != expected_status and status != ProjectStatus.FAILED:
            time.sleep(1)
            status = get_project_status(test_client, project_uid)

        assert status == expected_status
