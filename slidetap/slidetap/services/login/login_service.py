"""Metaclass for login service."""
from abc import ABCMeta, abstractmethod

from flask.wrappers import Response as FlaskResponse
from slidetap.model.session import Session
from slidetap.flask_extension import FlaskExtension


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
    def get_current_session(self) -> Session:
        """Return session of current user."""
        raise NotImplementedError()

    @abstractmethod
    def login(self, session: Session) -> FlaskResponse:
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
