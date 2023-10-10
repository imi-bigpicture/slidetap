"""Metaclass for authentication service."""
from abc import ABCMeta, abstractmethod
from slidetap.flask_extension import FlaskExtension
from slidetap.model.session import Session


class AuthService(FlaskExtension, metaclass=ABCMeta):
    @abstractmethod
    def logout(self, session: Session):
        """Logout user session."""
        raise NotImplementedError()

    @abstractmethod
    def check_permissions(self, session: Session) -> bool:
        """Check if user has permission to use service."""
        raise NotImplementedError()

    @abstractmethod
    def valid(self, session: Session) -> bool:
        """Return true if user session is valid."""
        raise NotImplementedError()

    @abstractmethod
    def keep_alive(self, session: Session) -> bool:
        """Keep user session alive."""
        raise NotImplementedError()


class AuthServiceException(Exception):
    """Exception for when authentication service fails."""

    def __init__(self, message: str):
        self._message = message

    def __str__(self) -> str:
        return self._message
