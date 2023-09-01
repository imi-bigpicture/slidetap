"""Login controller using oauth authentication."""
from flask import current_app, redirect, url_for

from slides.controller.login.login_controller import LoginController
from slides.services import LoginService, OauthAuthService


class OauthAuthLoginController(LoginController):
    def __init__(
        self,
        auth_service: OauthAuthService,
        login_service: LoginService,
    ):
        super().__init__(login_service)
        self._auth_service = auth_service

        @self.blueprint.route("/login")
        def login():
            redirect_uri = url_for("auth.authorize", _external=True)
            redirect_uri = "http://localhost:5001/api/auth/authorize"
            current_app.logger.debug(redirect_uri)
            return self.auth_service.authorize_redirect(redirect_uri)

        @self.blueprint.route("/authorize")
        def authorize():
            # token = self._application.authorize_access_token()
            # self.login_service.login(token)
            return redirect("http://localhost:3001")

    @property
    def auth_service(self) -> OauthAuthService:
        return self._auth_service
