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

"""Metaclass for basic auth authentication service."""
from abc import abstractmethod
from typing import Optional

from slidetap.web.model import UserSession
from slidetap.web.services.auth.auth_service import AuthService


class BasicAuthService(AuthService):
    @abstractmethod
    def login(self, username: str, password: str) -> Optional[UserSession]:
        """Login user by username and password. Return Session if login
        successful."""
        raise NotImplementedError()
