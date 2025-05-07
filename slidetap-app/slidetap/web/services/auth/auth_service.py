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

"""Metaclass for authentication service."""
from abc import ABCMeta, abstractmethod

from slidetap.model.session import UserSession
from slidetap.web.flask_extension import FlaskExtension


class AuthService(FlaskExtension, metaclass=ABCMeta):
    @abstractmethod
    def logout(self, session: UserSession):
        """Logout user session."""
        raise NotImplementedError()

    @abstractmethod
    def check_permissions(self, session: UserSession) -> bool:
        """Check if user has permission to use service."""
        raise NotImplementedError()

    @abstractmethod
    def valid(self, session: UserSession) -> bool:
        """Return true if user session is valid."""
        raise NotImplementedError()

    @abstractmethod
    def keep_alive(self, session: UserSession) -> bool:
        """Keep user session alive."""
        raise NotImplementedError()


class AuthServiceException(Exception):
    """Exception for when authentication service fails."""

    def __init__(self, message: str):
        self._message = message

    def __str__(self) -> str:
        return self._message
