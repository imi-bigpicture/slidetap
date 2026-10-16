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

from slidetap.services import ImageService
from slidetap.web.routers import image_router
from slidetap.web.routers.image_router import MAX_THUMBNAIL_SIZE
from slidetap.web.services import LoginService


@pytest.fixture()
def image_service(decoy: Decoy):
    return decoy.mock(cls=ImageService)


@pytest.fixture()
def test_client(decoy: Decoy, simple_app: FastAPI, image_service: ImageService):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: image_service, provides=ImageService)
    container = make_async_container(service_provider)
    simple_app.include_router(image_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapImageRouter:
    @pytest.mark.parametrize(
        ("width", "height"),
        [
            (MAX_THUMBNAIL_SIZE + 1, 512),
            (512, MAX_THUMBNAIL_SIZE + 1),
            (0, 512),
            (512, -1),
        ],
    )
    def test_a_thumbnail_outside_the_size_limits_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        image_service: ImageService,
        width: int,
        height: int,
    ):
        # Act
        response = test_client.get(
            f"api/images/image/{uuid4()}/thumbnail",
            params={"width": width, "height": height},
        )

        # Assert
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        decoy.verify(
            image_service.get_thumbnail(Anything(), Anything(), Anything(), Anything()),
            times=0,
        )

    def test_a_thumbnail_at_the_size_limit_is_made(
        self,
        decoy: Decoy,
        test_client: TestClient,
        image_service: ImageService,
    ):
        # Arrange
        image_uid = uuid4()
        decoy.when(
            image_service.get_thumbnail(
                image_uid, MAX_THUMBNAIL_SIZE, MAX_THUMBNAIL_SIZE, "png"
            )
        ).then_return(b"thumbnail")

        # Act
        response = test_client.get(
            f"api/images/image/{image_uid}/thumbnail",
            params={"width": MAX_THUMBNAIL_SIZE, "height": MAX_THUMBNAIL_SIZE},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.content == b"thumbnail"
