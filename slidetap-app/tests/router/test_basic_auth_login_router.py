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

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from slidetap.config import LoginConfig
from slidetap.external_interfaces import AuthInterface
from slidetap.model import UserSession
from slidetap.web.routers.login_router import login_router
from slidetap.web.services.login_service import LoginService


@pytest.fixture()
def login_config():

    return LoginConfig("a-test-secret-key-that-is-32-bytes")


@pytest.fixture()
def auth_interface(decoy: Decoy):
    return decoy.mock(cls=AuthInterface)


@pytest.fixture()
def login_service(decoy: Decoy):
    return decoy.mock(cls=LoginService)


@pytest.fixture()
def basic_auth_login_router_app(
    simple_app: FastAPI,
    login_config: LoginConfig,
    auth_interface: AuthInterface,
    login_service: LoginService,
):

    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: auth_interface, provides=AuthInterface)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: login_config, provides=LoginConfig)
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
    def test_login_valid(
        self,
        decoy: Decoy,
        auth_interface: AuthInterface,
        login_service: LoginService,
        test_client: TestClient,
    ):
        # Arrange
        username = "user"
        password = "pass"
        form = {"username": username, "password": password}
        session = UserSession(username="valid_user", token="token")
        decoy.when(auth_interface.login(username, password)).then_return(session)
        decoy.when(auth_interface.check_permissions(session)).then_return(True)

        # Act
        response = test_client.post(
            "/api/auth/login", json=form, headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(login_service.set_login_cookies(Anything(), session), times=1)

    def test_login_forbidden(
        self,
        decoy: Decoy,
        auth_interface: AuthInterface,
        test_client: TestClient,
    ):
        # Arrange
        username = "user"
        password = "pass"
        form = {"username": username, "password": password}
        session = UserSession(username="valid_user", token="token")
        decoy.when(auth_interface.login(username, password)).then_return(session)
        decoy.when(auth_interface.check_permissions(session)).then_return(False)

        # Act
        response = test_client.post(
            "/api/auth/login", json=form, headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_login_unauthorized(
        self,
        decoy: Decoy,
        auth_interface: AuthInterface,
        test_client: TestClient,
    ):
        # Arrange
        username = "user"
        password = "pass"
        form = {"username": username, "password": password}
        decoy.when(auth_interface.login(username, password)).then_return(None)

        # Act
        response = test_client.post(
            "/api/auth/login", json=form, headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_login_unprocessable_entity(
        self,
        test_client: TestClient,
    ):
        # Arrange
        form = {}

        # Act
        response = test_client.post(
            "/api/auth/login", json=form, headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_logout_ends_the_session_with_the_auth_interface(
        self,
        decoy: Decoy,
        auth_interface: AuthInterface,
        login_service: LoginService,
        test_client: TestClient,
    ):
        # Arrange
        decoy.when(login_service.verify_access_and_csrf_tokens(Anything())).then_return(
            {"sub": "user", LoginService.SESSION_CLAIM: "token"}
        )

        # Act
        response = test_client.post("/api/auth/logout")

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(
            auth_interface.logout(UserSession(username="user", token="token")),
            times=1,
        )
        decoy.verify(login_service.unset_login_cookies(Anything()), times=1)

    def test_logout_of_a_token_without_a_session_unsets_the_cookies(
        self,
        decoy: Decoy,
        auth_interface: AuthInterface,
        login_service: LoginService,
        test_client: TestClient,
    ):
        # Arrange
        decoy.when(login_service.verify_access_and_csrf_tokens(Anything())).then_return(
            {"sub": "user"}
        )

        # Act
        response = test_client.post("/api/auth/logout")

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(auth_interface.logout(Anything()), times=0)
        decoy.verify(login_service.unset_login_cookies(Anything()), times=1)

    @pytest.mark.parametrize(
        "status_code", [HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED]
    )
    def test_logout_not_logged_in(
        self,
        decoy: Decoy,
        login_service: LoginService,
        test_client: TestClient,
        status_code: HTTPStatus,
    ):
        # Arrange
        decoy.when(login_service.verify_access_and_csrf_tokens(Anything())).then_raise(
            HTTPException(status_code=status_code)
        )

        # Act
        response = test_client.post("/api/auth/logout")

        # Assert
        assert response.status_code == status_code

    def test_keep_alive_logged_in(
        self,
        decoy: Decoy,
        auth_interface: AuthInterface,
        login_service: LoginService,
        test_client: TestClient,
    ):
        # Arrange
        session = UserSession(username="user", token="token")
        decoy.when(login_service.verify_access_and_csrf_tokens(Anything())).then_return(
            {"sub": "user", LoginService.SESSION_CLAIM: "token"}
        )
        decoy.when(auth_interface.valid(session)).then_return(True)
        decoy.when(auth_interface.keep_alive(session)).then_return(True)

        # Act
        response = test_client.post("/api/auth/keepAlive")

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(login_service.set_login_cookies(Anything(), session), times=1)

    @pytest.mark.parametrize(("valid", "kept_alive"), [(False, True), (True, False)])
    def test_keep_alive_of_a_session_the_auth_interface_ended_is_refused(
        self,
        decoy: Decoy,
        auth_interface: AuthInterface,
        login_service: LoginService,
        test_client: TestClient,
        valid: bool,
        kept_alive: bool,
    ):
        """A logged out session, or one of a user the auth interface no longer
        accepts, does not get a new access token."""
        # Arrange
        session = UserSession(username="user", token="token")
        decoy.when(login_service.verify_access_and_csrf_tokens(Anything())).then_return(
            {"sub": "user", LoginService.SESSION_CLAIM: "token"}
        )
        decoy.when(auth_interface.valid(session)).then_return(valid)
        decoy.when(auth_interface.keep_alive(session)).then_return(kept_alive)

        # Act
        response = test_client.post("/api/auth/keepAlive")

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        decoy.verify(login_service.set_login_cookies(Anything(), Anything()), times=0)

    def test_keep_alive_of_a_token_without_a_session_is_refused(
        self,
        decoy: Decoy,
        login_service: LoginService,
        test_client: TestClient,
    ):
        # Arrange
        decoy.when(login_service.verify_access_and_csrf_tokens(Anything())).then_return(
            {"sub": "user"}
        )

        # Act
        response = test_client.post("/api/auth/keepAlive")

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        decoy.verify(login_service.set_login_cookies(Anything(), Anything()), times=0)

    @pytest.mark.parametrize(
        "status_code", [HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED]
    )
    def test_keep_alive_not_logged_in(
        self,
        decoy: Decoy,
        login_service: LoginService,
        test_client: TestClient,
        status_code: HTTPStatus,
    ):
        # Arrange
        decoy.when(login_service.verify_access_and_csrf_tokens(Anything())).then_raise(
            HTTPException(status_code=status_code)
        )

        # Act
        response = test_client.post("/api/auth/keepAlive")

        # Assert
        assert response.status_code == status_code
