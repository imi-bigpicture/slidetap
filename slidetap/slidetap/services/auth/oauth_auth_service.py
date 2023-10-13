"""Metaclass for oauth authentication service."""
from abc import ABCMeta, abstractmethod
from typing import Optional

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client.apps import FlaskOAuth2App
from flask import Flask

from slidetap.config import Config
from slidetap.services.auth.auth_service import AuthService
from slidetap.model.session import Session


class OauthAuthService(AuthService, metaclass=ABCMeta):
    def __init__(self, app: Optional[Flask] = None):
        self._oauth = OAuth()
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        self._oauth.init_app(app)
        self._application = self.create_application()

    @abstractmethod
    def create_application(self) -> FlaskOAuth2App:
        raise NotImplementedError()

    def logout(self, session: Session):
        """Logout user session."""
        raise NotImplementedError()

    def check_permissions(self, session: Session) -> bool:
        """Check if user has permission to use service."""
        raise NotImplementedError()

    def valid(self, session: Session) -> bool:
        """Return true if user session is valid."""
        raise NotImplementedError()

    def keep_alive(self, session: Session) -> bool:
        """Keep user session alive."""
        raise NotImplementedError()

    def authorize_redirect(self, redirect_url: str):
        return self._application.authorize_redirect(redirect_url)


class OpenIdAuthService(OauthAuthService):
    def create_application(self) -> FlaskOAuth2App:
        client_id = Config.env_get("SLIDETAP_CLIENT_ID")
        client_secret = Config.env_get("SLIDETAP_CLIENT_SECRET")
        metadata = Config.env_get("SLIDETAP_OPENID_METADATA")

        application = self._oauth.register(
            "slidetap",
            server_metadata_url=metadata,
            client_id=client_id,
            client_sectret=client_secret,
        )
        assert isinstance(application, FlaskOAuth2App)
        return application
