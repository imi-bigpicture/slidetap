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

import pytest
from decoy import Decoy
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.application_policy import ApplicationPolicy
from slidetap.web.routers import application_router
from slidetap.web.services import LoginService


@pytest.fixture()
def test_client(decoy: Decoy, simple_app: FastAPI):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(
        lambda: ApplicationPolicy(pre_processes_images_separately=False),
        provides=ApplicationPolicy,
    )
    container = make_async_container(service_provider)
    simple_app.include_router(application_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapApplicationRouter:
    def test_the_policy_says_whether_images_are_pre_processed_separately(
        self, test_client: TestClient
    ):
        # Act
        response = test_client.get("api/application/policy")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"preProcessesImagesSeparately": False}
