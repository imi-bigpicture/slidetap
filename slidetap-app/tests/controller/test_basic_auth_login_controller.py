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

import json
from http import HTTPStatus
from pathlib import Path
from typing import Dict, Optional

import pytest
from flask import Flask
from flask.testing import FlaskClient
from slidetap.config import ConfigTest
from slidetap.services.auth import HardCodedBasicAuthTestService
from slidetap.web.controller import BasicAuthLoginController
from tests.test_classes import DummyLoginService


@pytest.fixture()
def simple_app():
    config = ConfigTest(Path(""))
    app = Flask(__name__)
    app.config.from_object(config)
    yield app


@pytest.fixture()
def basic_auth_login_controller(simple_app: Flask):
    auth_service = HardCodedBasicAuthTestService({"username": "valid"})
    login_service = DummyLoginService()
    controller = BasicAuthLoginController(auth_service, login_service)
    simple_app.register_blueprint(controller.blueprint, url_prefix="/api/auth")
    yield simple_app


@pytest.fixture()
def test_client(basic_auth_login_controller: Flask):
    yield basic_auth_login_controller.test_client()


@pytest.mark.unittest
class TestSlideTapAuth:
    @pytest.mark.parametrize(
        "form, expected_response",
        [
            (None, HTTPStatus.BAD_REQUEST),
            ({"username": "username"}, HTTPStatus.BAD_REQUEST),
            ({"password": "password"}, HTTPStatus.BAD_REQUEST),
            ({"username": "username", "password": "valid"}, HTTPStatus.OK),
        ],
    )
    def test_login(
        self,
        test_client: FlaskClient,
        form: Optional[Dict[str, str]],
        expected_response: HTTPStatus,
    ):
        response = test_client.post(
            "/api/auth/login", data=json.dumps(form), content_type="application/json"
        )
        assert response.status_code == expected_response
