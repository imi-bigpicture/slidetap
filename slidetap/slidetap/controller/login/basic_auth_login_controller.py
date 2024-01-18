"""Login controller using basic auth authentication."""
from http import HTTPStatus

from flask import current_app, make_response, request
from flask.wrappers import Response as FlaskResponse

from slidetap.controller.login.login_controller import LoginController
from slidetap.serialization import BasicAuthModel
from slidetap.services import BasicAuthService, LoginService


class BasicAuthLoginController(LoginController):
    def __init__(
        self,
        auth_service: BasicAuthService,
        login_service: LoginService,
    ):
        super().__init__(login_service)
        self._auth_service = auth_service

        @self.blueprint.route("/login", methods=["POST"])
        def login() -> FlaskResponse:
            """Login user using credentials in login form.

            Returns
            ----------
            Response
                Response with token if valid login. Status 'UNAUTHORIZED' if
                wrong login, 'BAD_REQUEST' if username and password not in
                request.
            """
            try:
                login_data = BasicAuthModel().load(request.get_json())
                if not isinstance(login_data, dict):
                    raise ValueError()
            except Exception:
                return make_response(
                    "Missing username or password", HTTPStatus.BAD_REQUEST
                )
            username = login_data["username"]
            password = login_data["password"]
            current_app.logger.debug(f"Logging for user {username}.")
            session = self.auth_service.login(username, password)
            if session is None:
                current_app.logger.info(f"Wrong user or password for user {username}.")
                return make_response(
                    {"msg": "Wrong user or password."}, HTTPStatus.UNAUTHORIZED
                )
            if not self.auth_service.check_permissions(session):
                current_app.logger.info(
                    f"User {username} has not permission to use service."
                )
                return make_response(
                    {"msg": "User has not permission to use service."},
                    HTTPStatus.UNAUTHORIZED,
                )
            current_app.logger.debug(f"Login successful for user {username}")
            return self.login_service.login(session)

        @self.blueprint.route("/logout", methods=["POST"])
        @self.login_service.validate_auth()
        def logout() -> FlaskResponse:
            """Logout user."""
            current_app.logger.debug("Logout user.")
            session = self.login_service.get_current_session()
            self.auth_service.logout(session)
            return self.login_service.logout()

        @self.blueprint.route("/keepAlive", methods=["POST"])
        @self.login_service.validate_auth()
        def keep_alive() -> FlaskResponse:
            current_app.logger.debug("Keepalive.")
            session = self.login_service.get_current_session()
            self.auth_service.keep_alive(session)
            return make_response()

    @property
    def auth_service(self) -> BasicAuthService:
        return self._auth_service
