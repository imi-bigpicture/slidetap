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
from typing import Dict, Optional

import pytest
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slidetap.config import Config, ConfigTest
from slidetap.web.routers.login_router import login_router
from slidetap.web.services.auth import HardCodedBasicAuthTestService
from slidetap.web.services.auth.basic_auth_service import BasicAuthService
from slidetap.web.services.login_service import LoginService
from tests.test_classes import DummyLoginService


@pytest.fixture()
def basic_auth_login_router_app(simple_app: FastAPI, config: ConfigTest):

    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(
        lambda: HardCodedBasicAuthTestService({"username": "valid"}),
        provides=BasicAuthService,
    )
    service_provider.provide(DummyLoginService, provides=LoginService)
    service_provider.provide(lambda: config, provides=Config)
    container = make_async_container(service_provider)
    simple_app.include_router(login_router, tags=["auth"])
    setup_dishka(container, simple_app)
    yield simple_app


@pytest.fixture()
def test_client(basic_auth_login_router_app: FastAPI):
    with TestClient(basic_auth_login_router_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapBasicAuthLoginRouter:
    @pytest.mark.parametrize(
        "form, expected_response",
        [
            (None, HTTPStatus.UNPROCESSABLE_ENTITY),
            ({"username": "username"}, HTTPStatus.UNPROCESSABLE_ENTITY),
            ({"password": "password"}, HTTPStatus.UNPROCESSABLE_ENTITY),
            ({"username": "username", "password": "valid"}, HTTPStatus.OK),
        ],
    )
    def test_login(
        self,
        test_client: TestClient,
        form: Optional[Dict[str, str]],
        expected_response: HTTPStatus,
    ):
        response = test_client.post(
            "/api/auth/login", json=form, headers={"Content-Type": "application/json"}
        )
        assert response.status_code == expected_response
