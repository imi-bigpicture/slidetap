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
from typing import Any, Dict

import jwt
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import HTTPException, Request, Response

from slidetap.config import LoginConfig


class LoginService:
    ALGORITM = "HS256"

    def __init__(self, config: LoginConfig):
        self._secret_key = config.secret_key
        self._access_token_expiration_seconds = config.access_token_expiration_seconds

    def _create_jwt_token(self, data: dict) -> str:
        """Create a JWT token with the given data."""
        to_encode = data.copy()
        expire = int(time.time()) + self._access_token_expiration_seconds
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self._secret_key, algorithm=self.ALGORITM)

    def _verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify a JWT token and return the payload."""
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self.ALGORITM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid token",
            )

    def verify_access_and_csrf_tokens(self, request: Request) -> Dict[str, Any]:
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

    def set_login_cookies(self, response: Response, user: str):
        """Set login cookies in the response."""
        jwt_token = self._create_jwt_token({"sub": user})
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


@inject
def require_valid_token(
    request: Request, login_service: FromDishka[LoginService]
) -> Dict[str, Any]:
    """Dependency to require a valid token for a request.

    This will verify the access and CSRF tokens from the request cookies.
    If the tokens are valid, it will return the user payload.
    If not, it will raise an HTTPException with status code 401 or 403.

    Note: This does NOT refresh the session. Use this for read-only operations
    like checking session status, where you don't want to extend the session.
    """
    return login_service.verify_access_and_csrf_tokens(request)


@inject
def require_valid_token_and_refresh(
    request: Request, response: Response, login_service: FromDishka[LoginService]
) -> Dict[str, Any]:
    """Dependency to require login and refresh the session.

    This will verify the access and CSRF tokens from the request cookies.
    If the tokens are valid, it will refresh the session and return the user payload.
    If not, it will raise an HTTPException with status code 401 or 403.

    Note: This refreshes the session on every authenticated request, so active
    users will never be logged out due to inactivity. Use this for normal API
    operations (CRUD, etc.).
    """
    user_payload = login_service.verify_access_and_csrf_tokens(request)
    login_service.set_login_cookies(response, user_payload["sub"])
    return user_payload
