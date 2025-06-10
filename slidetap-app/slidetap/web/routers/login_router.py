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

"""FastAPI router for authentication."""
import logging
from http import HTTPStatus

from another_fastapi_jwt_auth import AuthJWT
from fastapi import Depends, HTTPException
from pydantic import BaseModel

from slidetap.model.basic_auth_credentials import BasicAuthCredentials
from slidetap.web.routers.router import Router, SecuredRouter
from slidetap.web.services import BasicAuthService


class LoginResponse(BaseModel):
    """Response model for successful login."""

    msg: str = "login successful"
    # Add other fields that the login service returns


class LogoutResponse(BaseModel):
    """Response model for logout."""

    msg: str = "logout successful"


class KeepAliveResponse(BaseModel):
    """Response model for keep alive."""

    status: str = "ok"


class Settings(BaseModel):
    authjwt_secret_key: str = "secret"
    # Configure application to store and get JWT from cookies
    authjwt_token_location: set = {"cookies"}
    # Disable CSRF Protection for this example. default is True
    authjwt_cookie_csrf_protect: bool = False


@AuthJWT.load_config
def get_config():
    return Settings()


class LoginRouter(SecuredRouter):
    """FastAPI router for authentication."""

    def __init__(
        self,
        auth_service: BasicAuthService,
    ):
        self._auth_service = auth_service
        self._logger = logging.getLogger(__name__)
        super().__init__()

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all authentication routes."""

        @self.router.post("/login")
        async def login(
            credentials: BasicAuthCredentials, Authorize: AuthJWT = Depends()
        ) -> LoginResponse:
            """Login user using credentials.

            Parameters
            ----------
            credentials: BasicAuthCredentials
                User credentials

            Returns
            ----------
            LoginResponse
                Response with token if valid login.
            """
            self._logger.debug(f"Logging for user {credentials.username}.")
            session = self._auth_service.login(
                credentials.username, credentials.password
            )
            if session is None:
                self._logger.error(
                    f"Wrong user or password for user {credentials.username}."
                )
                raise HTTPException(
                    status_code=HTTPStatus.UNAUTHORIZED,
                    detail="Wrong user or password.",
                )
            if not self._auth_service.check_permissions(session):
                self._logger.error(
                    f"User {credentials.username} has not permission to use service."
                )
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail="User has not permission to use service.",
                )
            self._logger.debug(f"Login successful for user {credentials.username}")

            access_token = Authorize.create_access_token(subject=session.username)
            refresh_token = Authorize.create_refresh_token(subject=session.username)
            Authorize.set_access_cookies(access_token)
            Authorize.set_refresh_cookies(refresh_token)

            return LoginResponse()

        @self.router.post("/logout")
        async def logout(
            user=self.auth_dependency(), Authorize: AuthJWT = Depends()
        ) -> LogoutResponse:
            """Logout user.

            Returns
            ----------
            LogoutResponse
                Logout confirmation
            """
            self._logger.debug("Logout user.")
            Authorize.unset_jwt_cookies()
            return LogoutResponse()

        @self.router.post("/keepAlive")
        async def keep_alive(
            user=self.auth_dependency(), Authorize: AuthJWT = Depends()
        ) -> KeepAliveResponse:
            """Keep user session alive.

            Returns
            ----------
            KeepAliveResponse
                Keep alive confirmation
            """
            self._logger.debug("Keepalive.")
            new_access_token = Authorize.create_access_token(subject=user)
            Authorize.set_access_cookies(new_access_token)
            return KeepAliveResponse()

    @property
    def auth_service(self) -> BasicAuthService:
        """Return the authentication service."""
        return self._auth_service
