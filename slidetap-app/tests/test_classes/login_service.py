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

from functools import wraps
from http import HTTPStatus

from flask import make_response
from flask.wrappers import Response as FlaskResponse
from slidetap.model import UserSession
from slidetap.web.services import LoginService


class DummyLoginService(LoginService):
    def validate_auth(self):
        def wrapper(fn):
            @wraps(fn)
            def decorator(*args, **kwargs) -> FlaskResponse:
                return fn(*args, **kwargs)

            return decorator

        return wrapper

    def get_current_user(self) -> str:
        """Return username of current user."""
        return "test user"

    def get_current_session(self) -> UserSession:
        return UserSession("test user", "token")

    def login(self, session: UserSession) -> FlaskResponse:
        return make_response("", HTTPStatus.OK)

    def logout(self) -> FlaskResponse:
        return make_response("", HTTPStatus.OK)

    def refresh(self, response: FlaskResponse) -> FlaskResponse:
        return response
