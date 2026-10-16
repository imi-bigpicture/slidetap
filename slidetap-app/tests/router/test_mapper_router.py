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

from http import HTTPStatus
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.model import CodeAttribute, MappingItem
from slidetap.model.mapper import MappingItemCreate
from slidetap.services import MapperService
from slidetap.web.routers import mapper_router
from slidetap.web.services import LoginService


@pytest.fixture()
def mapper_service(decoy: Decoy):
    return decoy.mock(cls=MapperService)


@pytest.fixture()
def test_client(decoy: Decoy, simple_app: FastAPI, mapper_service: MapperService):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: mapper_service, provides=MapperService)
    container = make_async_container(service_provider)
    simple_app.include_router(mapper_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapMapperRouter:
    @pytest.mark.parametrize(
        ("expression", "reason"),
        [("(unclosed", "not a valid regular expression"), ("(a+)+$", "exponential")],
    )
    def test_creating_a_mapping_with_an_unsafe_expression_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        code_attribute: CodeAttribute,
        expression: str,
        reason: str,
    ):
        # Arrange
        mapping = MappingItemCreate(
            mapper_uid=uuid4(), expression=expression, attribute=code_attribute
        )

        # Act
        response = test_client.post(
            "api/mappers/mappings/create",
            json=mapping.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert reason in response.json()["detail"]
        decoy.verify(mapper_service.create_mapping(Anything()), times=0)

    def test_updating_a_mapping_with_an_unsafe_expression_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        mapping = MappingItem(
            uid=uuid4(),
            mapper_uid=uuid4(),
            expression="(unclosed",
            attribute=code_attribute,
        )

        # Act
        response = test_client.post(
            f"api/mappers/mappings/mapping/{mapping.uid}",
            json=mapping.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "not a valid regular expression" in response.json()["detail"]
        decoy.verify(mapper_service.update_mapping(Anything()), times=0)

    def test_creating_a_mapping_with_a_safe_expression_is_saved(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        mapping = MappingItemCreate(
            mapper_uid=uuid4(), expression="Hematoxylin.*", attribute=code_attribute
        )
        created = MappingItem(
            uid=uuid4(),
            mapper_uid=mapping.mapper_uid,
            expression=mapping.expression,
            attribute=code_attribute,
        )
        decoy.when(mapper_service.create_mapping(Anything())).then_return(created)

        # Act
        response = test_client.post(
            "api/mappers/mappings/create",
            json=mapping.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
