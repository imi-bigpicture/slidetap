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
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.web.routers import health_router


@pytest.fixture()
def test_client(simple_app: FastAPI):
    container = make_async_container(Provider(scope=Scope.APP))
    simple_app.include_router(health_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapHealthRouter:
    def test_status_is_ok_without_a_login(self, test_client: TestClient):
        """The health check needs no token, so nothing to log in with is provided."""
        # Act
        response = test_client.get("api/health/status")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "ok"}
