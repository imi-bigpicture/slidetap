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
from typing import Any, Dict

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from slidetap.external_interfaces import AuthInterface
from slidetap.model.basic_auth_credentials import BasicAuthCredentials
from slidetap.web.services.login_service import (
    LoginService,
    require_valid_token,
    require_valid_token_and_refresh,
)


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


class SessionStatusResponse(BaseModel):
    """Response model for session status."""

    exp: int
    user: str


login_router = APIRouter(prefix="/api/auth", tags=["auth"], route_class=DishkaRoute)


@login_router.post("/login")
async def login(
    response: Response,
    credentials: BasicAuthCredentials,
    auth_interface: FromDishka[AuthInterface],
    login_service: FromDishka[LoginService],
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
    logging.debug(f"Logging for user {credentials.username}.")
    session = auth_interface.login(credentials.username, credentials.password)
    if session is None:
        logging.error(f"Wrong user or password for user {credentials.username}.")
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Wrong user or password.",
        )
    if not auth_interface.check_permissions(session):
        logging.error(f"User {credentials.username} has not permission to use service.")
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="User has not permission to use service.",
        )
    logging.debug(f"Login successful for user {credentials.username}")
    login_service.set_login_cookies(response, session.username)

    return LoginResponse()


@login_router.post("/logout")
async def logout(
    response: Response,
    login_service: FromDishka[LoginService],
    user_payload: Dict[str, Any] = Depends(require_valid_token),
) -> LogoutResponse:
    """Logout user.

    Returns
    ----------
    LogoutResponse
        Logout confirmation

    """
    logging.debug(f"Logout user {user_payload}.")
    login_service.unset_login_cookies(response)
    return LogoutResponse()


@login_router.post("/keepAlive")
async def keep_alive(
    response: Response,
    login_service: FromDishka[LoginService],
    user_payload: Dict[str, Any] = Depends(require_valid_token_and_refresh),
) -> KeepAliveResponse:
    """Keep user session alive.

    Returns
    ----------
    KeepAliveResponse
        Keep alive confirmation
    """
    logging.debug("Keepalive.")
    login_service.set_login_cookies(response, user_payload["sub"])
    return KeepAliveResponse()


@login_router.get("/session_status")
async def get_session_status(
    user_payload: Dict[str, Any] = Depends(require_valid_token),
) -> SessionStatusResponse:
    """Get current session expiration info.

    Returns
    ----------
    SessionStatusResponse
        Session status with expiration timestamp

    Note: This endpoint uses require_valid_token (not require_valid_token_and_refresh) so it
    does NOT refresh the session. This allows accurate monitoring of when
    the session will actually expire.
    """
    logging.debug(f"Session status for user {user_payload['sub']}.")
    return SessionStatusResponse(
        exp=user_payload["exp"],
        user=user_payload["sub"],
    )
