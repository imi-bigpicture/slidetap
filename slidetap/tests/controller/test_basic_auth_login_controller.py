import json
from typing import Dict, Optional
from http import HTTPStatus
from flask.testing import FlaskClient
from slidetap.config import ConfigTest

import pytest
from flask import Flask

from slidetap.test_classes import TestAuthService
from slidetap.test_classes import TestLoginService
from slidetap.controller import BasicAuthLoginController


@pytest.fixture()
def simple_app():
    config = ConfigTest()
    app = Flask(__name__)
    app.config.from_object(config)
    yield app


@pytest.fixture()
def basic_auth_login_controller(simple_app: Flask):
    auth_service = TestAuthService()
    login_service = TestLoginService()
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
