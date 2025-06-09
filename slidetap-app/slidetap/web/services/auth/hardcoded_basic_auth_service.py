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

from typing import Dict, Optional

from slidetap.model import UserSession
from slidetap.web.services.auth.auth_service import AuthServiceException
from slidetap.web.services.auth.basic_auth_service import BasicAuthService


class HardCodedBasicAuthTestService(BasicAuthService):
    def __init__(self, credentials: Dict[str, str]):
        self._credentials = credentials

    def login(self, username: str, password: str) -> Optional[UserSession]:
        if username not in self._credentials or password != self._credentials[username]:
            return None
        return UserSession(username=username, token="token")

    def logout(self, session: UserSession):
        return True

    def check_permissions(self, session: UserSession) -> bool:
        return True

    def valid(self, session: UserSession) -> bool:
        return True

    def keep_alive(self, session: UserSession) -> bool:
        return True
