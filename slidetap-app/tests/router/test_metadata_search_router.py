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

from slidetap.model import MetadataSearchItem, NotAllowedActionError
from slidetap.model.metadata_import_status import MetadataImportStatus
from slidetap.web.routers import metadata_search_router
from slidetap.web.services import LoginService, MetadataImportService


@pytest.fixture()
def metadata_import_service(decoy: Decoy):
    return decoy.mock(cls=MetadataImportService)


@pytest.fixture()
def test_client(
    decoy: Decoy,
    simple_app: FastAPI,
    metadata_import_service: MetadataImportService,
):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(
        lambda: metadata_import_service, provides=MetadataImportService
    )
    container = make_async_container(service_provider)
    simple_app.include_router(metadata_search_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapMetadataSearchRouter:
    @pytest.mark.parametrize("supports_retry", [True, False])
    def test_whether_retry_is_supported_is_answered(
        self,
        decoy: Decoy,
        test_client: TestClient,
        metadata_import_service: MetadataImportService,
        supports_retry: bool,
    ):
        # Arrange
        decoy.when(metadata_import_service.supports_retry).then_return(supports_retry)

        # Act
        response = test_client.get("api/metadata-search/supports-retry")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() is supports_retry

    def test_the_search_items_of_a_batch_are_listed(
        self,
        decoy: Decoy,
        test_client: TestClient,
        metadata_import_service: MetadataImportService,
    ):
        # Arrange
        batch_uid = uuid4()
        search_item = MetadataSearchItem(
            uid=uuid4(),
            batch_uid=batch_uid,
            identifier="case 1",
            schema_uid=uuid4(),
            status=MetadataImportStatus.FAILED,
            message="Not found",
            search_parameters={"case": "1"},
        )
        decoy.when(metadata_import_service.list_search_items(batch_uid)).then_return(
            [search_item]
        )

        # Act
        response = test_client.get(
            "api/metadata-search/items", params={"batchUid": str(batch_uid)}
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        listed = response.json()
        assert [item["uid"] for item in listed] == [str(search_item.uid)]
        assert "searchParameters" not in listed[0]

    def test_listing_search_items_without_a_batch_is_refused(
        self, test_client: TestClient
    ):
        # Act
        response = test_client.get("api/metadata-search/items")

        # Assert
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_a_failed_search_item_is_retried(
        self,
        decoy: Decoy,
        test_client: TestClient,
        metadata_import_service: MetadataImportService,
    ):
        # Arrange
        search_item_uid = uuid4()

        # Act
        response = test_client.post(
            f"api/metadata-search/items/{search_item_uid}/retry"
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(
            metadata_import_service.retry_search_item(search_item_uid), times=1
        )

    @pytest.mark.parametrize(
        ("error", "status_code"),
        [
            (NotAllowedActionError("Batch is not in progress"), HTTPStatus.CONFLICT),
            (ValueError("Search item is not failed"), HTTPStatus.BAD_REQUEST),
        ],
    )
    def test_a_refused_retry_is_answered_with_its_status(
        self,
        decoy: Decoy,
        test_client: TestClient,
        metadata_import_service: MetadataImportService,
        error: Exception,
        status_code: HTTPStatus,
    ):
        # Arrange
        search_item_uid = uuid4()
        decoy.when(
            metadata_import_service.retry_search_item(search_item_uid)
        ).then_raise(error)

        # Act
        response = test_client.post(
            f"api/metadata-search/items/{search_item_uid}/retry"
        )

        # Assert
        assert response.status_code == status_code

    def test_a_search_item_is_excluded(
        self,
        decoy: Decoy,
        test_client: TestClient,
        metadata_import_service: MetadataImportService,
    ):
        # Arrange
        search_item_uid = uuid4()

        # Act
        response = test_client.post(
            f"api/metadata-search/items/{search_item_uid}/exclude"
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(
            metadata_import_service.exclude_search_item(search_item_uid), times=1
        )
