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

# Pydantic does not support dumping missing/optional fields as `undefined`.
# In Python and JSON, missing fields are either omitted (default) or set to `null` if present with a None value.
# JavaScript's `undefined` does not exist in JSON or Python.
# To omit missing fields, use `model.model_dump(exclude_unset=True)` or `model.model_dump_json(exclude_unset=True)`.
