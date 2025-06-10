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

"""Base router classes for FastAPI."""
from abc import ABCMeta
from http import HTTPStatus
from typing import Any, Dict

from another_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel


class Settings(BaseModel):
    authjwt_secret_key: str = "secret"
    # Configure application to store and get JWT from cookies
    authjwt_token_location: set = {"cookies"}
    # Disable CSRF Protection for this example. default is True
    authjwt_cookie_csrf_protect: bool = False


@AuthJWT.load_config
def get_config():
    return Settings()


class Router(metaclass=ABCMeta):
    """Base class for a FastAPI router."""

    def __init__(self):
        """Create a base router."""
        self._router = APIRouter()

    @property
    def router(self) -> APIRouter:
        """Return the APIRouter for the router."""
        return self._router

    # def return_json(self, item: Any) -> Dict[str, Any]:
    #     """Return JSON response."""
    #     if hasattr(item, "model_dump"):
    #         return item.model_dump(mode="json", by_alias=True)
    #     return item

    # def return_not_found(self) -> None:
    #     """Raise HTTP 404 Not Found exception."""
    #     raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Not found")

    # def return_bad_request(self, detail: str = "Bad request") -> None:
    #     """Raise HTTP 400 Bad Request exception."""
    #     raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=detail)

    def return_ok(self) -> Dict[str, str]:
        """Return OK response."""
        return {"status": "ok"}

    def return_image(self, image: bytes, mimetype: str) -> Response:
        """Return image response."""
        return Response(content=image, media_type=mimetype)


class SecuredRouter(Router):
    """Router that requires the user to have a valid session."""

    def get_current_user(self, Authorize: AuthJWT = Depends()) -> str:
        """Dependency to validate authentication."""
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()
        if not isinstance(current_user, str):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="User is not authenticated",
            )
        return current_user

    def auth_dependency(self):
        """Return the authentication dependency for route protection."""
        return Depends(self.get_current_user)
