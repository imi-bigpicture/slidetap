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

import json
import random
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Dict, Optional

from slidetap.config import ConfigParser
from slidetap.external_interfaces.auth import AuthInterface
from slidetap.model import UserSession


@dataclass(frozen=True)
class JsonFileAuthConfig:
    credentials_file: Path
    salt: str

    @classmethod
    def parse(cls, parser: ConfigParser) -> "JsonFileAuthConfig":
        if not parser.contains_yaml_key("json_file_auth"):
            raise KeyError("Missing 'json_file_auth' configuration section.")
        parser = parser.get_sub_parser("json_file_auth")
        credentials_file = parser.get_yaml("credentials_file")
        salt = parser.get_yaml("salt")
        if salt is None or salt == "" or len(salt) < 32:
            raise ValueError("Salt must be at least 32 characters long.")
        return JsonFileAuthConfig(
            credentials_file=Path(credentials_file),
            salt=salt,
        )


class JsonFileAuthInterface(AuthInterface):
    def __init__(self, json_file_auth_config: JsonFileAuthConfig):
        self._credentials = self._load_credentials(
            json_file_auth_config.credentials_file
        )
        self._salt = json_file_auth_config.salt
        self._sessions: Dict[str, UserSession] = {}

    def login(self, username: str, password: str) -> Optional[UserSession]:
        if not self._login_is_valid(username, password):
            return None
        session = self._create_session(username)
        self._sessions[username] = session
        return session

    def logout(self, session: UserSession):
        if not self._session_is_valid(session):
            return False
        self._sessions.pop(session.username)
        return True

    def check_permissions(self, session: UserSession) -> bool:
        if not self._session_is_valid(session):
            return False
        return True

    def valid(self, session: UserSession) -> bool:
        return self._session_is_valid(session)

    def keep_alive(self, session: UserSession) -> bool:
        return self._session_is_valid(session)

    def _create_session(self, username: str) -> UserSession:
        token = sha256(str(random.getrandbits(256)).encode()).hexdigest()
        return UserSession(username=username, token=token)

    def _login_is_valid(self, username: str, password: str) -> bool:
        if username not in self._credentials:
            return False
        expected_hashed_password = self._credentials[username]
        hashed_password = sha256((password + self._salt).encode()).hexdigest()
        return hashed_password == expected_hashed_password

    def _session_is_valid(self, session: UserSession) -> bool:
        stored_session = self._sessions.get(session.username)
        if stored_session is None:
            return False
        return stored_session.token == session.token

    def _load_credentials(self, credential_file: Path) -> Dict[str, str]:
        with open(credential_file, "r") as file:
            credentials = json.load(file)
        assert isinstance(credentials, dict)
        for key, value in credentials.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
        return credentials

    @staticmethod
    def write_credentials(
        credentials: Dict[str, str], salt: str, credential_file: Path
    ):
        """Write credentials to the credential file.

        Parameters
        ----------
        credentials: Dict[str, str]
            A dictionary mapping usernames to plaintext passwords.
        """
        hashed_credentials = {
            username: sha256((password + salt).encode()).hexdigest()
            for username, password in credentials.items()
        }
        with open(credential_file, "w") as file:
            json.dump(hashed_credentials, file)
