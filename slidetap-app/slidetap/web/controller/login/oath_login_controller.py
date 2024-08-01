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

"""Login controller using oauth authentication."""
from flask import current_app, redirect, url_for
from slidetap.web.controller.login.login_controller import LoginController
from slidetap.web.services import LoginService, OauthAuthService


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
