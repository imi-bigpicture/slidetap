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

from slidetap.model import Dataset, ProjectNotEditableError
from slidetap.services import DatasetService
from slidetap.task import Scheduler
from slidetap.web import SlideTapWebAppFactory
from slidetap.web.routers import dataset_router
from slidetap.web.services import LoginService


@pytest.fixture()
def dataset_service(decoy: Decoy):
    return decoy.mock(cls=DatasetService)


@pytest.fixture()
def scheduler(decoy: Decoy):
    return decoy.mock(cls=Scheduler)


@pytest.fixture()
def test_client(
    decoy: Decoy,
    simple_app: FastAPI,
    dataset_service: DatasetService,
    scheduler: Scheduler,
):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: dataset_service, provides=DatasetService)
    service_provider.provide(lambda: scheduler, provides=Scheduler)
    container = make_async_container(service_provider)
    simple_app.include_router(dataset_router)
    simple_app.add_exception_handler(
        ProjectNotEditableError, SlideTapWebAppFactory._refuse_change
    )
    setup_dishka(container, simple_app)
    with TestClient(simple_app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapDatasetRouter:
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", "api/datasets/importable"),
            ("GET", "api/datasets"),
            ("DELETE", f"api/datasets/dataset/{uuid4()}"),
        ],
    )
    def test_unimplemented_endpoints_answer_not_implemented(
        self, test_client: TestClient, method: str, path: str
    ):
        # Act
        response = test_client.request(method, path)

        # Assert
        assert response.status_code == HTTPStatus.NOT_IMPLEMENTED

    def test_import_dataset_answers_not_implemented(
        self, test_client: TestClient, dataset: Dataset
    ):
        # Act
        response = test_client.post(
            "api/datasets/import",
            json=dataset.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.NOT_IMPLEMENTED

    def test_a_dataset_is_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
        dataset: Dataset,
    ):
        # Arrange
        decoy.when(dataset_service.get_optional(dataset.uid)).then_return(dataset)

        # Act
        response = test_client.get(f"api/datasets/dataset/{dataset.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == dataset.model_dump(mode="json", by_alias=True)

    def test_a_dataset_that_is_not_there_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
    ):
        # Arrange
        dataset_uid = uuid4()
        decoy.when(dataset_service.get_optional(dataset_uid)).then_return(None)

        # Act
        response = test_client.get(f"api/datasets/dataset/{dataset_uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_dataset_answers_with_the_dataset_as_stored(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
        dataset: Dataset,
    ):
        # Arrange
        stored = dataset.model_copy(update={"name": "stored name"})
        decoy.when(dataset_service.update(dataset)).then_return(stored)

        # Act
        response = test_client.post(
            f"api/datasets/dataset/{dataset.uid}",
            json=dataset.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["name"] == "stored name"

    def test_update_of_a_dataset_that_is_not_there_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
        dataset: Dataset,
    ):
        # Arrange
        decoy.when(dataset_service.update(dataset)).then_return(None)

        # Act
        response = test_client.post(
            f"api/datasets/dataset/{dataset.uid}",
            json=dataset.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_remap_of_a_dataset_is_scheduled(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
        scheduler: Scheduler,
        dataset: Dataset,
    ):
        # Arrange
        decoy.when(dataset_service.get_optional(dataset.uid)).then_return(dataset)

        # Act
        response = test_client.post(f"api/datasets/dataset/{dataset.uid}/remap")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "scheduled"}
        decoy.verify(scheduler.remap_dataset_attributes(dataset.uid), times=1)

    def test_remap_of_a_dataset_that_is_not_there_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
        scheduler: Scheduler,
    ):
        # Arrange
        dataset_uid = uuid4()
        decoy.when(dataset_service.get_optional(dataset_uid)).then_return(None)

        # Act
        response = test_client.post(f"api/datasets/dataset/{dataset_uid}/remap")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
        decoy.verify(scheduler.remap_dataset_attributes(Anything()), times=0)

    def test_remap_of_a_dataset_that_cannot_be_changed_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
        scheduler: Scheduler,
        dataset: Dataset,
    ):
        # Arrange
        decoy.when(dataset_service.get_optional(dataset.uid)).then_return(dataset)
        decoy.when(dataset_service.assert_can_change(dataset.uid)).then_raise(
            ProjectNotEditableError(uuid4(), "view only")
        )

        # Act
        response = test_client.post(f"api/datasets/dataset/{dataset.uid}/remap")

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT
        decoy.verify(scheduler.remap_dataset_attributes(Anything()), times=0)

    def test_remap_that_fails_to_be_scheduled_is_a_server_error(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
        scheduler: Scheduler,
        dataset: Dataset,
    ):
        # Arrange
        decoy.when(dataset_service.get_optional(dataset.uid)).then_return(dataset)
        decoy.when(scheduler.remap_dataset_attributes(dataset.uid)).then_raise(
            RuntimeError("queue is down")
        )

        # Act
        response = test_client.post(f"api/datasets/dataset/{dataset.uid}/remap")

        # Assert
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to schedule the remap, try again"
