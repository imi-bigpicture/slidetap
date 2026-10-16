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
from decoy.matchers import Anything, IsA
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.model import Code, CodeAttribute, CodeSuggestion, MappingItem
from slidetap.services import AttributeService, MapperService
from slidetap.web.routers import attribute_router
from slidetap.web.services import LoginService


@pytest.fixture()
def attribute_service(decoy: Decoy):
    return decoy.mock(cls=AttributeService)


@pytest.fixture()
def mapper_service(decoy: Decoy):
    return decoy.mock(cls=MapperService)


@pytest.fixture()
def test_client(
    decoy: Decoy,
    simple_app: FastAPI,
    attribute_service: AttributeService,
    mapper_service: MapperService,
):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: attribute_service, provides=AttributeService)
    service_provider.provide(lambda: mapper_service, provides=MapperService)
    container = make_async_container(service_provider)
    simple_app.include_router(attribute_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.fixture()
def mappable_attribute(code_attribute: CodeAttribute) -> CodeAttribute:
    return code_attribute.model_copy(update={"mappable_value": "hematoxylin"})


@pytest.fixture()
def mapping(mappable_attribute: CodeAttribute) -> MappingItem:
    return MappingItem(
        uid=uuid4(),
        mapper_uid=uuid4(),
        expression="hematoxylin",
        attribute=mappable_attribute,
    )


@pytest.mark.unittest
class TestSlideTapAttributeRouter:
    def test_an_attribute_is_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        decoy.when(attribute_service.get_optional(code_attribute.uid)).then_return(
            code_attribute
        )

        # Act
        response = test_client.get(f"api/attributes/attribute/{code_attribute.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == code_attribute.model_dump(mode="json", by_alias=True)

    def test_an_attribute_that_is_not_there_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
    ):
        # Arrange
        attribute_uid = uuid4()
        decoy.when(attribute_service.get_optional(attribute_uid)).then_return(None)

        # Act
        response = test_client.get(f"api/attributes/attribute/{attribute_uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_of_an_attribute_that_is_not_there_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        decoy.when(attribute_service.update(Anything())).then_return(None)

        # Act
        response = test_client.post(
            f"api/attributes/attribute/{code_attribute.uid}",
            json=code_attribute.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_an_attribute_is_created_of_its_value_type(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        decoy.when(attribute_service.create(IsA(CodeAttribute))).then_return(
            code_attribute
        )

        # Act
        response = test_client.post(
            f"api/attributes/create/{code_attribute.schema_uid}",
            json=code_attribute.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(code_attribute.uid)

    def test_an_attribute_of_another_schema_is_not_created(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
    ):
        # Act
        response = test_client.post(
            f"api/attributes/create/{uuid4()}",
            json=code_attribute.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(attribute_service.create(Anything()), times=0)

    def test_an_attribute_without_a_value_type_is_not_created(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        data = code_attribute.model_dump(mode="json", by_alias=True)
        del data["attributeValueType"]

        # Act
        response = test_client.post(
            f"api/attributes/create/{code_attribute.schema_uid}", json=data
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(attribute_service.create(Anything()), times=0)

    def test_the_mapping_an_attribute_was_mapped_with_is_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        mapper_service: MapperService,
        mappable_attribute: CodeAttribute,
        mapping: MappingItem,
    ):
        # Arrange
        mapped_attribute = mappable_attribute.model_copy(
            update={"mapping_item_uid": mapping.uid}
        )
        decoy.when(attribute_service.get_optional(mapped_attribute.uid)).then_return(
            mapped_attribute
        )
        decoy.when(mapper_service.get_mapping(mapping.uid)).then_return(mapping)

        # Act
        response = test_client.get(
            f"api/attributes/attribute/{mapped_attribute.uid}/mapping"
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(mapping.uid)
        decoy.verify(mapper_service.get_mapping_for_attribute(Anything()), times=0)

    def test_the_mapping_of_an_attribute_not_mapped_yet_is_looked_up(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        mapper_service: MapperService,
        mappable_attribute: CodeAttribute,
        mapping: MappingItem,
    ):
        # Arrange
        decoy.when(attribute_service.get_optional(mappable_attribute.uid)).then_return(
            mappable_attribute
        )
        decoy.when(
            mapper_service.get_mapping_for_attribute(mappable_attribute)
        ).then_return(mapping)

        # Act
        response = test_client.get(
            f"api/attributes/attribute/{mappable_attribute.uid}/mapping"
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(mapping.uid)

    def test_the_mapping_of_an_attribute_without_a_mappable_value_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        mapper_service: MapperService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        decoy.when(attribute_service.get_optional(code_attribute.uid)).then_return(
            code_attribute
        )

        # Act
        response = test_client.get(
            f"api/attributes/attribute/{code_attribute.uid}/mapping"
        )

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
        decoy.verify(mapper_service.get_mapping_for_attribute(Anything()), times=0)

    def test_the_mapping_of_an_attribute_no_mapping_matches_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        mapper_service: MapperService,
        mappable_attribute: CodeAttribute,
    ):
        # Arrange
        decoy.when(attribute_service.get_optional(mappable_attribute.uid)).then_return(
            mappable_attribute
        )
        decoy.when(
            mapper_service.get_mapping_for_attribute(mappable_attribute)
        ).then_return(None)

        # Act
        response = test_client.get(
            f"api/attributes/attribute/{mappable_attribute.uid}/mapping"
        )

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Mapping not found"

    def test_codes_for_a_schema_are_searched_with_the_query_and_limit(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
    ):
        # Arrange
        attribute_schema_uid = uuid4()
        suggestion = CodeSuggestion(
            code=Code(code="H", scheme="scheme", meaning="Hematoxylin"),
            match="meaning",
        )
        decoy.when(
            mapper_service.search_codes_for_attribute_schema(
                attribute_schema_uid, "hema", 5
            )
        ).then_return([suggestion])

        # Act
        response = test_client.get(
            f"api/attributes/schema/{attribute_schema_uid}/codes/search",
            params={"q": "hema", "limit": 5},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == [suggestion.model_dump(mode="json", by_alias=True)]

    def test_the_attributes_of_a_schema_are_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        decoy.when(
            attribute_service.get_for_schema(code_attribute.schema_uid)
        ).then_return([code_attribute])

        # Act
        response = test_client.get(f"api/attributes/schema/{code_attribute.schema_uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert [attribute["uid"] for attribute in response.json()] == [
            str(code_attribute.uid)
        ]
