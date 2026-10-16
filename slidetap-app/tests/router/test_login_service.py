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

import pytest
from fastapi import Response
from starlette.requests import Request

from slidetap.config import MIN_SECRET_KEY_BYTES, ConfigParser, LoginConfig
from slidetap.model import UserSession
from slidetap.web.services.login_service import LoginService

SECRET_KEY = "a-test-secret-key-that-is-32-bytes"


def _request_with_cookies(response: Response) -> Request:
    """A request carrying the cookies a response set, with the CSRF header."""
    cookies = {
        header.split("=", 1)[0]: header.split("=", 1)[1].split(";", 1)[0]
        for name, header in (
            (raw_name.decode(), raw_value.decode())
            for raw_name, raw_value in response.raw_headers
        )
        if name == "set-cookie"
    }
    cookie_header = "; ".join(f"{name}={value}" for name, value in cookies.items())
    return Request(
        {
            "type": "http",
            "headers": [
                (b"cookie", cookie_header.encode()),
                (b"x-csrf-token", cookies["csrf_token"].encode()),
            ],
        }
    )


@pytest.mark.unittest
class TestLoginService:
    def test_the_access_token_carries_the_session_it_was_issued_for(self):
        # Arrange
        login_service = LoginService(LoginConfig(SECRET_KEY))
        session = UserSession(username="user", token="session token")
        response = Response()

        # Act
        login_service.set_login_cookies(response, session)
        payload = login_service.verify_access_and_csrf_tokens(
            _request_with_cookies(response)
        )

        # Assert
        assert payload["sub"] == "user"
        assert LoginService.session_from_payload(payload) == session

    @pytest.mark.parametrize(
        "payload", [{}, {"sub": "user"}, {LoginService.SESSION_CLAIM: "token"}]
    )
    def test_a_payload_without_a_session_gives_none(self, payload: dict):
        assert LoginService.session_from_payload(payload) is None


@pytest.mark.unittest
class TestLoginConfig:
    def test_a_secret_key_shorter_than_the_minimum_is_refused(self):
        # Arrange
        parser = ConfigParser(
            config={}, env={"SLIDETAP_SECRET_KEY": "x" * (MIN_SECRET_KEY_BYTES - 1)}
        )

        # Act & Assert
        with pytest.raises(ValueError, match="SLIDETAP_SECRET_KEY"):
            LoginConfig.parse(parser)

    def test_a_secret_key_of_the_minimum_length_is_accepted(self):
        # Arrange
        parser = ConfigParser(
            config={}, env={"SLIDETAP_SECRET_KEY": "x" * MIN_SECRET_KEY_BYTES}
        )

        # Act
        config = LoginConfig.parse(parser)

        # Assert
        assert config.secret_key == "x" * MIN_SECRET_KEY_BYTES
