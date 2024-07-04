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

"""Login service using JSON web tokens."""
from datetime import datetime, timedelta, timezone
from functools import wraps
from http import HTTPStatus
from secrets import token_urlsafe
from typing import Callable, Optional

from flask import Flask, current_app, jsonify, make_response
from flask.wrappers import Response as FlaskResponse
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt,
    get_jwt_identity,
    set_access_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
)
from flask_jwt_extended.exceptions import NoAuthorizationError

from slidetap.config import Config
from slidetap.model.session import Session
from slidetap.services.login.login_service import LoginService


class JwtLoginService(LoginService):
    """Implementation of LoginService using Json web tokens."""

    def __init__(self, config: Config, app: Optional[Flask] = None):
        self._jwt_cookie_secure = config.webapp_url.startswith("https://")
        self._keepalive_interval = timedelta(seconds=config.keepalive)
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initiate LoginService with Flask-app."""
        super().init_app(app)
        app.config["JWT_SECRET_KEY"] = token_urlsafe()
        app.config["JWT_COOKIE_CSRF_PROTECT"] = True
        # app.config['JWT_ACCESS_CSRF_COOKIE_PATH'] = '/api'
        app.config["JWT_TOKEN_LOCATION"] = "cookies"
        app.config["JWT_COOKIE_SAMESITE"] = "Strict"
        app.config["JWT_ACCESS_COOKIE_PATH"] = "/api"
        app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 2 * self._keepalive_interval
        app.config["JWT_COOKIE_SECURE"] = self._jwt_cookie_secure
        self._jwt = JWTManager(app)

    def validate_auth(self):
        """Wrapper for checking that user has access to protected routes."""

        def wrapper(fn: Callable[..., FlaskResponse]):
            @wraps(fn)
            def decorator(*args, **kwargs) -> FlaskResponse:
                # current_app.logger.debug("Validating auth.")
                try:
                    verify_jwt_in_request()
                    # current_app.logger.debug("Validated auth.")
                    return fn(*args, **kwargs)
                except NoAuthorizationError as exception:
                    current_app.logger.error(f"Failed to validate auth. {exception}")
                    return make_response("", HTTPStatus.UNAUTHORIZED)

            return decorator

        return wrapper

    def get_current_user(self) -> str:
        """Return username of current user."""
        return self.get_current_session().username

    def get_current_session(self) -> Session:
        """Return username of current user."""
        identity = get_jwt_identity()
        return Session(identity["username"], identity["token"])

    def login(self, session: Session) -> FlaskResponse:
        """Return response with jwt access cookies."""
        current_app.logger.debug(
            f"Setting access token for session {session.username}."
        )
        response = jsonify({"msg": "login successful"})
        access_token = create_access_token(identity=session)
        set_access_cookies(response, access_token)
        return response

    def logout(self) -> FlaskResponse:
        """Unset jwt cookies."""
        response = jsonify({"msg": "logout successful"})
        unset_jwt_cookies(response)
        return response

    def refresh(self, response: FlaskResponse) -> FlaskResponse:
        """Refresh jwt if needed."""
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + self._keepalive_interval)
        if target_timestamp > exp_timestamp:
            identity = get_jwt_identity()
            access_token = create_access_token(identity=identity)
            set_access_cookies(response, access_token)
        return response
