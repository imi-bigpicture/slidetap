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

"""Metaclass for login service."""
from abc import ABCMeta, abstractmethod

from flask.wrappers import Response as FlaskResponse
from slidetap.flask_extension import FlaskExtension
from slidetap.web.model.session import UserSession


class LoginService(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for performing log in/out of user and validating that
    user is logged in."""

    @abstractmethod
    def validate_auth(self):
        """Wrapper for checking that user has access to protected routes."""
        raise NotImplementedError()

    @abstractmethod
    def get_current_user(self) -> str:
        """Return username of current user."""
        raise NotImplementedError()

    @abstractmethod
    def get_current_session(self) -> UserSession:
        """Return session of current user."""
        raise NotImplementedError()

    @abstractmethod
    def login(self, session: UserSession) -> FlaskResponse:
        """Return response with access token set."""
        raise NotImplementedError()

    @abstractmethod
    def logout(self) -> FlaskResponse:
        """Return response with access token unset."""
        raise NotImplementedError()

    @abstractmethod
    def refresh(self, response: FlaskResponse) -> FlaskResponse:
        """Return response with, if needed, refreshed access token."""
        raise NotImplementedError()
