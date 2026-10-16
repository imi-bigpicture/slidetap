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

from slidetap.model import NotAllowedActionError, NotFoundError
from slidetap.services import ItemService, MapperService
from slidetap.web import SlideTapWebAppFactory
from slidetap.web.routers import item_router
from slidetap.web.services import (
    ImagePipelineService,
    LoginService,
    MetadataExportService,
)


@pytest.fixture()
def image_pipeline_service(decoy: Decoy):
    return decoy.mock(cls=ImagePipelineService)


@pytest.fixture()
def test_client(
    decoy: Decoy,
    simple_app: FastAPI,
    image_pipeline_service: ImagePipelineService,
):
    login_service = decoy.mock(cls=LoginService)
    item_service = decoy.mock(cls=ItemService)
    mapper_service = decoy.mock(cls=MapperService)
    metadata_export_service = decoy.mock(cls=MetadataExportService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: item_service, provides=ItemService)
    service_provider.provide(lambda: mapper_service, provides=MapperService)
    service_provider.provide(
        lambda: metadata_export_service, provides=MetadataExportService
    )
    service_provider.provide(
        lambda: image_pipeline_service, provides=ImagePipelineService
    )
    container = make_async_container(service_provider)
    simple_app.include_router(item_router)
    simple_app.add_exception_handler(NotFoundError, SlideTapWebAppFactory._not_found)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapItemRouter:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "status_code"),
        [
            (NotAllowedActionError("The project is view only"), HTTPStatus.CONFLICT),
            (NotFoundError("Image does not exist."), HTTPStatus.NOT_FOUND),
        ],
    )
    async def test_a_retry_refused_for_one_image_retries_none(
        self,
        decoy: Decoy,
        test_client: TestClient,
        image_pipeline_service: ImagePipelineService,
        error: Exception,
        status_code: HTTPStatus,
    ):
        """Every image is checked before any is queued."""
        # Arrange
        image_uids = [uuid4(), uuid4()]
        decoy.when(image_pipeline_service.assert_can_retry(image_uids)).then_raise(
            error
        )

        # Act
        response = test_client.post(
            "api/items/retry", json=[str(image_uid) for image_uid in image_uids]
        )

        # Assert
        assert response.status_code == status_code
        decoy.verify(await image_pipeline_service.retry(Anything()), times=0)

    @pytest.mark.asyncio
    async def test_a_retry_of_images_that_can_be_retried_retries_each(
        self,
        decoy: Decoy,
        test_client: TestClient,
        image_pipeline_service: ImagePipelineService,
    ):
        # Arrange
        image_uids = [uuid4(), uuid4()]

        # Act
        response = test_client.post(
            "api/items/retry", json=[str(image_uid) for image_uid in image_uids]
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        for image_uid in image_uids:
            decoy.verify(await image_pipeline_service.retry(image_uid), times=1)
