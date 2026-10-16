#    Copyright 2026 SECTRA AB
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
from decoy import Decoy
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slidetap_example import ExampleSchema

from slidetap.model import NotFoundError, RootSchema, RootSchemaIndex
from slidetap.services import SchemaService
from slidetap.web import SlideTapWebAppFactory
from slidetap.web.routers import schema_router
from slidetap.web.services import LoginService


@pytest.fixture()
def schema_service(decoy: Decoy):
    return decoy.mock(cls=SchemaService)


@pytest.fixture()
def default_root(schema: ExampleSchema) -> RootSchemaIndex:
    return RootSchemaIndex(schema=schema, is_default=True)


@pytest.fixture()
def other_root(other_schema: RootSchema) -> RootSchemaIndex:
    return RootSchemaIndex(schema=other_schema, is_default=False)


@pytest.fixture()
def test_client(
    decoy: Decoy,
    simple_app: FastAPI,
    schema_service: SchemaService,
    default_root: RootSchemaIndex,
    other_root: RootSchemaIndex,
):
    login_service = decoy.mock(cls=LoginService)
    decoy.when(schema_service.default_root).then_return(default_root)
    decoy.when(schema_service.get_root(other_root.uid)).then_return(other_root)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: schema_service, provides=SchemaService)
    container = make_async_container(service_provider)
    simple_app.include_router(schema_router)
    simple_app.add_exception_handler(NotFoundError, SlideTapWebAppFactory._not_found)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapSchemaRouter:
    def test_every_root_is_listed_with_which_new_projects_use(
        self,
        decoy: Decoy,
        test_client: TestClient,
        schema_service: SchemaService,
        default_root: RootSchemaIndex,
        other_root: RootSchemaIndex,
    ):
        # Arrange
        decoy.when(schema_service.roots).then_return(
            {default_root.uid: default_root, other_root.uid: other_root}
        )

        # Act
        response = test_client.get("api/schemas/roots")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert {root["uid"]: root["newProjects"] for root in response.json()} == {
            str(default_root.uid): True,
            str(other_root.uid): False,
        }

    def test_a_root_is_got_by_uid(
        self, test_client: TestClient, other_root: RootSchemaIndex
    ):
        # Act
        response = test_client.get(f"api/schemas/root/{other_root.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(other_root.uid)

    def test_a_root_that_is_not_provided_is_not_found(
        self, decoy: Decoy, test_client: TestClient, schema_service: SchemaService
    ):
        # Arrange
        root_schema_uid = uuid4()
        decoy.when(schema_service.get_root(root_schema_uid)).then_raise(
            NotFoundError(f"Root schema {root_schema_uid} not found.")
        )

        # Act
        response = test_client.get(f"api/schemas/root/{root_schema_uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_the_root_without_a_uid_is_the_root_of_new_projects(
        self, test_client: TestClient, default_root: RootSchemaIndex
    ):
        # Act
        response = test_client.get("api/schemas/root")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(default_root.uid)

    def test_the_root_with_a_uid_is_that_root(
        self, test_client: TestClient, other_root: RootSchemaIndex
    ):
        # Act
        response = test_client.get(
            "api/schemas/root", params={"rootSchemaUid": str(other_root.uid)}
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(other_root.uid)

    def test_the_attribute_schemas_are_of_the_root_asked_for(
        self, test_client: TestClient, other_root: RootSchemaIndex
    ):
        # Act
        response = test_client.get(
            "api/schemas/attributes", params={"rootSchemaUid": str(other_root.uid)}
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert {attribute["uid"] for attribute in response.json()} == {
            str(attribute.uid) for attribute in other_root.get_attributes()
        }

    def test_an_attribute_schema_is_got_across_roots(
        self,
        decoy: Decoy,
        test_client: TestClient,
        schema_service: SchemaService,
        schema: ExampleSchema,
    ):
        # Arrange
        attribute_schema = schema.patient.attributes["sex"]
        decoy.when(schema_service.get_any_attribute(attribute_schema.uid)).then_return(
            attribute_schema
        )

        # Act
        response = test_client.get(f"api/schemas/attribute/{attribute_schema.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(attribute_schema.uid)

    @pytest.mark.parametrize("error", [KeyError("missing"), ValueError("missing")])
    def test_an_attribute_schema_no_root_has_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        schema_service: SchemaService,
        error: Exception,
    ):
        # Arrange
        attribute_schema_uid = uuid4()
        decoy.when(schema_service.get_any_attribute(attribute_schema_uid)).then_raise(
            error
        )

        # Act
        response = test_client.get(f"api/schemas/attribute/{attribute_schema_uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_an_item_schema_is_got_from_the_root_of_new_projects(
        self, test_client: TestClient, schema: ExampleSchema
    ):
        # Act
        response = test_client.get(f"api/schemas/item/{schema.patient_schema_uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(schema.patient_schema_uid)

    def test_an_item_schema_the_root_does_not_have_is_null(
        self, test_client: TestClient
    ):
        # Act
        response = test_client.get(f"api/schemas/item/{uuid4()}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() is None

    def test_the_hierarchy_of_an_item_schema_includes_it(
        self, test_client: TestClient, schema: ExampleSchema
    ):
        # Act
        response = test_client.get(
            f"api/schemas/item/{schema.patient_schema_uid}/hierarchy"
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert str(schema.patient_schema_uid) in {
            item_schema["uid"] for item_schema in response.json()
        }

    def test_the_hierarchy_of_an_item_schema_the_root_does_not_have_is_not_found(
        self, test_client: TestClient
    ):
        # Act
        response = test_client.get(f"api/schemas/item/{uuid4()}/hierarchy")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
