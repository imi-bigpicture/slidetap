from typing import Optional

from slides.model import Session
from slides.services import AuthServiceException, BasicAuthService


class TestAuthService(BasicAuthService):
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
