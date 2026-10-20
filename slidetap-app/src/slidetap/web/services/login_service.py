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

import secrets
import time
from http import HTTPStatus
from typing import Any

import jwt
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import HTTPException, Request, Response

from slidetap.config import LoginConfig
from slidetap.model import UserSession


class LoginService:
    ALGORITHM = "HS256"
    SESSION_CLAIM = "sid"
    """Claim of the access token holding the auth interface session token."""
    KEEP_ALIVE_TIMEOUT_CLAIM = "kat"
    """Claim of the access token holding the keep alive timeout, in seconds, of
    the auth interface session."""
    KEEP_ALIVES_PER_LIFETIME = 3
    """How many keep alives the client is asked to send within the lifetime of
    an access token. The client only sends a keep alive if the user was active
    since the last one, so up to two intervals can pass between keep alives of
    an active user; three per lifetime keeps that within it."""

    def __init__(self, config: LoginConfig):
        self._secret_key = config.secret_key
        self._access_token_expiration_seconds = config.access_token_expiration_seconds
        self._keep_alive_interval_seconds = config.keep_alive_seconds

    def _create_jwt_token(self, data: dict, lifetime_seconds: int) -> str:
        """Create a JWT token with the given data, valid for the given time."""
        to_encode = data.copy()
        expire = int(time.time()) + lifetime_seconds
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self._secret_key, algorithm=self.ALGORITHM)

    def access_token_lifetime_seconds(self, session: UserSession | None) -> int:
        """How long an access token for the session is valid.

        The configured access token expiration, shortened to the keep alive
        timeout of the auth interface session, so that the access token expires
        no later than the session it carries.
        """
        if session is None or session.keep_alive_timeout_seconds is None:
            return self._access_token_expiration_seconds
        return min(
            self._access_token_expiration_seconds, session.keep_alive_timeout_seconds
        )

    def keep_alive_interval_seconds(self, session: UserSession | None) -> int:
        """How often the client should keep the session alive while in use.

        The configured keep alive interval, shortened so that an active user
        keeps both the access token and the auth interface session alive.
        """
        return max(
            1,
            min(
                self._keep_alive_interval_seconds,
                self.access_token_lifetime_seconds(session)
                // self.KEEP_ALIVES_PER_LIFETIME,
            ),
        )

    def _verify_jwt_token(self, token: str) -> dict[str, Any]:
        """Verify a JWT token and return the payload."""
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError as exception:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token has expired",
            ) from exception
        except jwt.InvalidTokenError as exception:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid token",
            ) from exception

    def verify_access_and_csrf_tokens(self, request: Request) -> dict[str, Any]:
        crsf_token_cookie = request.cookies.get("csrf_token")
        crsf_header_token = request.headers.get("X-CSRF-TOKEN")
        if (
            not crsf_header_token
            or not crsf_token_cookie
            or not secrets.compare_digest(crsf_header_token, crsf_token_cookie)
        ):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="CSRF token mismatch",
            )
        access_token_cookie = request.cookies.get("access_token")
        if not access_token_cookie:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Access token is missing",
            )
        return self._verify_jwt_token(access_token_cookie)

    def set_login_cookies(self, response: Response, session: UserSession):
        """Set login cookies in the response.

        The access token names the user and carries the token of the session
        the auth interface gave, so that the session can be checked and ended
        with the auth interface while the access token is valid. The access
        token expires no later than the auth interface times out the session.
        """
        claims: dict[str, Any] = {
            "sub": session.username,
            self.SESSION_CLAIM: session.token,
        }
        if session.keep_alive_timeout_seconds is not None:
            claims[self.KEEP_ALIVE_TIMEOUT_CLAIM] = session.keep_alive_timeout_seconds
        jwt_token = self._create_jwt_token(
            claims, self.access_token_lifetime_seconds(session)
        )
        crsf_token = secrets.token_urlsafe(32)
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            secure=True,
            samesite="strict",
        )
        response.set_cookie(
            key="csrf_token",
            value=crsf_token,
            httponly=False,
            secure=True,
            samesite="strict",
        )

    def unset_login_cookies(self, response: Response):
        """Unset login cookies in the response."""
        response.delete_cookie("access_token")
        response.delete_cookie("csrf_token")

    @classmethod
    def session_from_payload(cls, payload: dict[str, Any]) -> UserSession | None:
        """The auth interface session an access token was issued for.

        None for a token that carries no session.
        """
        username = payload.get("sub")
        token = payload.get(cls.SESSION_CLAIM)
        if not isinstance(username, str) or not isinstance(token, str):
            return None
        keep_alive_timeout_seconds = payload.get(cls.KEEP_ALIVE_TIMEOUT_CLAIM)
        if not isinstance(keep_alive_timeout_seconds, int):
            keep_alive_timeout_seconds = None
        return UserSession(
            username=username,
            token=token,
            keep_alive_timeout_seconds=keep_alive_timeout_seconds,
        )


@inject
def require_valid_token(
    request: Request, login_service: FromDishka[LoginService]
) -> dict[str, Any]:
    """Dependency to require a valid token for a request.

    This will verify the access and CSRF tokens from the request cookies.
    If the tokens are valid, it will return the user payload.
    If not, it will raise an HTTPException with status code 401 or 403.

    The session is not extended: a new access token is only issued by the
    keep alive endpoint.
    """
    return login_service.verify_access_and_csrf_tokens(request)
