"""Metaclass for basic auth authentication service."""
from abc import abstractmethod
from typing import Optional
from slidetap.services.auth.auth_service import AuthService


from slidetap.model import Session


class BasicAuthService(AuthService):
    @abstractmethod
    def login(self, username: str, password: str) -> Optional[Session]:
        """Login user by username and password. Return Session if login
        successful."""
        raise NotImplementedError()
