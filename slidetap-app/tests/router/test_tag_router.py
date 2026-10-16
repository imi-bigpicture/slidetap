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
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.model.tag import Tag
from slidetap.services.tag_service import TagService
from slidetap.web.routers import tag_router
from slidetap.web.services import LoginService


@pytest.fixture()
def tag_service(decoy: Decoy):
    return decoy.mock(cls=TagService)


@pytest.fixture()
def test_client(decoy: Decoy, simple_app: FastAPI, tag_service: TagService):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: tag_service, provides=TagService)
    container = make_async_container(service_provider)
    simple_app.include_router(tag_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.fixture()
def tag() -> Tag:
    return Tag(uid=uuid4(), name="tag name", description="about", color="#ff0000")


@pytest.mark.unittest
class TestSlideTapTagRouter:
    def test_every_tag_is_listed(
        self,
        decoy: Decoy,
        test_client: TestClient,
        tag_service: TagService,
        tag: Tag,
    ):
        # Arrange
        decoy.when(tag_service.get_all()).then_return([tag])

        # Act
        response = test_client.get("api/tags")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == [tag.model_dump(mode="json", by_alias=True)]

    def test_update_tag_saves_the_tag(
        self,
        decoy: Decoy,
        test_client: TestClient,
        tag_service: TagService,
        tag: Tag,
    ):
        # Arrange
        decoy.when(tag_service.update(tag)).then_return(tag)

        # Act
        response = test_client.post(
            f"api/tags/tag/{tag.uid}",
            json=tag.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(tag.uid)

    def test_update_tag_with_a_body_for_another_tag_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        tag_service: TagService,
        tag: Tag,
    ):
        # Arrange
        decoy.when(tag_service.update(Anything())).then_return(tag)

        # Act
        response = test_client.post(
            f"api/tags/tag/{uuid4()}",
            json=tag.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(tag_service.update(Anything()), times=0)
