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
import os
import shutil
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Mapping

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.datastructures import FileStorage
from werkzeug.test import TestResponse

from slidetap.apps.example import create_app
from slidetap.model import ImageStatus, ProjectStatus, ValueStatus


@pytest.fixture
def file():
    with io.BytesIO() as buffer:
        with open("tests/test_data/input.json", "rb") as input:
            buffer.write(input.read())
            buffer.seek(0)
        yield FileStorage(buffer, "input.json")


@pytest.fixture
def storage():
    with TemporaryDirectory() as storage_dir:
        yield Path(storage_dir)


@pytest.fixture
def app(storage: Path, tmpdir: str):
    os.environ["SLIDETAP_STORAGE"] = str(storage)
    os.environ["SLIDETAP_KEEPALIVE"] = str(1000)
    os.environ["SLIDETAP_DBURI"] = f"sqlite:///{tmpdir}/test.db"
    os.environ["SLIDETAP_WEBAPPURL"] = ""
    os.environ["SLIDETAP_ENFORCE_HTTPS"] = "false"
    os.environ["SLIDETAP_SECRET_KEY"] = ""
    with_mappers = ["fixation", "block_sampling", "embedding", "stain"]
    app = create_app(with_mappers=with_mappers)
    app.app_context().push()
    yield app


@pytest.fixture
def test_client(app: Flask):
    yield app.test_client()


def get_status(test_client: FlaskClient, uid: str):
    response = test_client.get(f"/api/project/{uid}")
    assert response.status_code == HTTPStatus.OK
    project = response.json
    assert project is not None
    assert isinstance(project, Mapping)
    assert project.get("uid", None) == uid
    status = project.get("status", None)
    assert status is not None
    assert isinstance(status, int)
    return ProjectStatus(status)


@pytest.mark.integration
class TestIntegration:
    @pytest.mark.timeout(60)
    def test_integration(
        self, test_client: FlaskClient, file: FileStorage, storage: Path
    ):
        schema_uid = "752ee40c-5ebe-48cf-b384-7001239ee70d"
        project_name = "integration project"
        # Login
        response = test_client.post(
            "/api/auth/login",
            data=json.dumps({"username": "user", "password": "valid"}),
            content_type="application/json",
        )
        assert response.status_code == HTTPStatus.OK
        cookies = SimpleCookie()
        for cookie in response.headers.getlist("Set-Cookie"):
            cookies.load(cookie)
        if "csrf_access_token" in cookies:
            csrf_token = cookies["csrf_access_token"].value
            headers = {"X-CSRF-TOKEN": csrf_token}
        else:
            headers = {}
        # Create project
        response = test_client.post(
            "/api/project/create",
            data=json.dumps({"name": project_name}),
            content_type="application/json",
            headers=headers,
        )
        project = self.assert_status_ok_and_parse_dict_json(response)
        project_uid = project.get("uid", None)
        assert project_uid is not None
        assert isinstance(project_uid, str)
        project_items: List[Dict[str, Any]] = project.get("items", None)
        assert project_items is not None
        assert isinstance(project_items, list)
        specimen_schema = next(
            item["schema"]["uid"]
            for item in project_items
            if item["schema"]["name"] == "specimen"
        )
        image_schema = next(
            item["schema"]["uid"]
            for item in project_items
            if item["schema"]["name"] == "wsi"
        )
        assert isinstance(image_schema, str)

        # Upload project file
        response = test_client.post(
            f"/api/project/{project_uid}/uploadFile",
            data={"file": file},
            headers=headers,
        )
        assert response.status_code == HTTPStatus.OK

        # Get status
        status = get_status(test_client, project_uid)
        assert status == ProjectStatus.METADATA_SEARCH_COMPLETE

        # Get collection schema
        response = test_client.get(
            f"/api/schema/attributes/{schema_uid}",
            headers=headers,
        )
        schemas = self.assert_status_ok_and_parse_list_json(response)
        collection_schema = next(
            (schema for schema in schemas if schema["tag"] == "collection"), None
        )
        assert collection_schema is not None

        # Get specimens
        response = test_client.get(
            f"/api/item/schema/{specimen_schema}/project/{project_uid}/items",
            headers=headers,
        )
        item_response = self.assert_status_ok_and_parse_dict_json(response)
        items = item_response["items"]
        assert len(items) == 2

        # Check specimen collection attributes
        for item in items:
            collection_attribute = next(
                attribute
                for attribute in item["attributes"].values()
                if attribute["schema"]["uid"] == collection_schema["uid"]
            )
            assert collection_attribute["mappingStatus"] == ValueStatus.NOT_MAPPED.value
            assert collection_attribute["displayValue"] == "Excision"

        # # Get attributes for collection schema
        # response = test_client.get(
        #     f"/api/attribute/schema/{collection_schema['uid']}",
        #     headers=headers,
        # )
        # attributes = self.assert_status_ok_and_parse_list_json(response)
        # collection_attribute = next(
        #     (
        #         attribute
        #         for attribute in attributes
        #         if attribute["schema"]["uid"] == collection_schema["uid"]
        #     ),
        #     None,
        # )
        # assert collection_attribute is not None
        # assert collection_attribute["mappingStatus"] == ValueStatus.NOT_MAPPED.value
        # assert collection_attribute["displayValue"] == "Excision"

        # Add mapper for collection schema attributes
        response = test_client.post(
            "/api/mapper/create",
            data=json.dumps(
                {"name": "collection", "attributeSchemaUid": collection_schema["uid"]}
            ),
            content_type="application/json",
            headers=headers,
        )
        mapper = self.assert_status_ok_and_parse_dict_json(response)

        # Add mapping for collection schema attributes
        mapped_value = {
            "meaning": "Excision",
            "scheme": "CUSTOM",
            "schemeVersion": None,
            "code": "Excision",
        }
        expression = "Excision"
        response = test_client.post(
            "/api/mapper/mapping/create",
            data=json.dumps(
                {
                    "uid": None,
                    "expression": expression,
                    "attribute": {
                        "value": mapped_value,
                        "schema": {"uid": collection_schema["uid"]},
                        "uid": None,
                        "mappableValue": None,
                    },
                    "mapperUid": mapper["uid"],
                }
            ),
            content_type="application/json",
            headers=headers,
        )
        mapping_item = self.assert_status_ok_and_parse_dict_json(response)

        assert mapping_item["uid"] is not None
        assert mapping_item["expression"] == expression
        assert mapping_item["attribute"]["value"] == mapped_value

        # Check that collection schema attributes are now mapped
        for item in items:
            collection_attribute = next(
                attribute
                for attribute in item["attributes"].values()
                if attribute["schema"]["uid"] == collection_schema["uid"]
            )
            response = test_client.get(
                f"/api/attribute/{collection_attribute['uid']}",
            )
            mapped_collection_attribute = self.assert_status_ok_and_parse_dict_json(
                response
            )
            assert mapped_collection_attribute["value"] == mapped_value

        # Update mapping item for collection schema attributes
        updated_mapped_value = {
            "meaning": "Excision 2",
            "scheme": "CUSTOM 2",
            "schemeVersion": None,
            "code": "Excision 2",
        }
        response = test_client.post(
            f"/api/mapper/mapping/{mapping_item['uid']}",
            data=json.dumps(
                {
                    "uid": mapping_item["uid"],
                    "expression": expression,
                    "attribute": {
                        "value": updated_mapped_value,
                        "schema": {"uid": collection_schema["uid"]},
                        "uid": None,
                        "mappableValue": None,
                    },
                    "mapperUid": mapper["uid"],
                }
            ),
            content_type="application/json",
            headers=headers,
        )
        updated_mapping_item = self.assert_status_ok_and_parse_dict_json(response)

        assert updated_mapping_item["uid"] == mapping_item["uid"]
        assert updated_mapping_item["expression"] == expression
        assert updated_mapping_item["attribute"]["value"] == updated_mapped_value

        # Check that attributes are now mapped to updated value
        for item in items:
            collection_attribute = next(
                attribute
                for attribute in item["attributes"].values()
                if attribute["schema"]["uid"] == collection_schema["uid"]
            )
            response = test_client.get(
                f"/api/attribute/{collection_attribute['uid']}",
            )
            mapped_collection_attribute = self.assert_status_ok_and_parse_dict_json(
                response
            )
            assert mapped_collection_attribute["value"] == updated_mapped_value

        # Download
        response = test_client.post(
            f"/api/project/{project_uid}/pre_process", headers=headers
        )
        assert response.status_code == HTTPStatus.OK

        # Get status until completed or failed
        time.sleep(1)
        status = get_status(test_client, project_uid)
        while (
            status != ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
            and status != ProjectStatus.FAILED
        ):
            time.sleep(1)
            status = get_status(test_client, project_uid)

        assert status == ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE

        # Get image status
        response = test_client.get(
            f"/api/item/schema/{image_schema}/project/{project_uid}/items",
            headers=headers,
        )
        images_response = self.assert_status_ok_and_parse_dict_json(response)
        images = images_response["items"]
        assert len(images) == 2
        for image in images:
            assert isinstance(image, Mapping)
            assert image.get("status") == ImageStatus.PRE_PROCESSED.value

        # Process
        response = test_client.post(
            f"/api/project/{project_uid}/process", headers=headers
        )
        assert response.status_code == HTTPStatus.OK

        # Get status until completed or failed
        time.sleep(1)
        status = get_status(test_client, project_uid)
        while (
            status != ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE
            and status != ProjectStatus.FAILED
        ):
            time.sleep(1)
            status = get_status(test_client, project_uid)

        assert status == ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE

        # Get image status
        response = test_client.get(
            f"/api/item/schema/{image_schema}/project/{project_uid}/items",
            headers=headers,
        )
        images_response = self.assert_status_ok_and_parse_dict_json(response)
        images = images_response["items"]
        assert len(images) == 2
        for image in images:
            assert isinstance(image, Mapping)
            assert image.get("status") == ImageStatus.POST_PROCESSED.value

        # Get thumbnails
        response = test_client.get(f"/api/image/thumbnails/{project_uid}")
        images_with_thumbnail = self.assert_status_ok_and_parse_list_json(response)

        for image in images_with_thumbnail:
            image_uid = image["uid"]
            response = test_client.get(f"/api/image/{image_uid}/thumbnail")
            assert response.status_code == HTTPStatus.OK

        # Get dzi and tile
        for image in images_with_thumbnail:
            image_uid = image["uid"]
            response = test_client.get(f"/api/image/{image_uid}")
            assert response.status_code == HTTPStatus.OK
            response = test_client.get(f"/api/image/{image_uid}/0/0_0.jpg")
            assert response.status_code == HTTPStatus.OK

        # Export to storage
        response = test_client.post(
            f"/api/project/{project_uid}/export", headers=headers
        )
        assert response.status_code == HTTPStatus.OK

        project_folder_name = f"{project_name}.{project_uid}"
        project_folder_path = storage.joinpath(project_folder_name)
        assert project_folder_path.exists()
        assert len(list(project_folder_path.iterdir())) == 3
        metadata_file = project_folder_path.joinpath("metadata", "metadata.json")
        assert metadata_file.exists()
        shutil.copy(metadata_file, r"c:/temp/metadata.json")

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
        response: TestResponse,
    ) -> Mapping[str, Any]:
        assert response.status_code == HTTPStatus.OK
        parsed = response.json
        assert isinstance(parsed, Mapping)
        return parsed

    @staticmethod
    def assert_status_ok_and_parse_list_json(
        response: TestResponse,
    ) -> List[Mapping[str, Any]]:
        assert response.status_code == HTTPStatus.OK
        parsed = response.json
        assert isinstance(parsed, list)
        return parsed
