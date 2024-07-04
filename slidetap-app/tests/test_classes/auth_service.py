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

from typing import Optional

from slidetap.model import Session
from slidetap.services import AuthServiceException, BasicAuthService


class AuthTestService(BasicAuthService):
    def login(self, username: str, password: str) -> Optional[Session]:
        if password == "valid":
            return Session(username, "token")
        return None

    def federated_login(self, login_key: str) -> Optional[Session]:
        if login_key == "valid":
            return Session("username", "token")
        return None

    def logout(self, session: Session):
        return True

    def check_permissions(self, session: Session) -> bool:
        return True

    def valid(self, session: Session) -> bool:
        return True

    def keep_alive(self, session: Session) -> bool:
        return True

    def has_access(self, session: Session, case_id: str) -> bool:
        if case_id == "auth no access":
            return False
        elif case_id == "auth fail":
            raise AuthServiceException("Testing AuthServiceException")
        return True
