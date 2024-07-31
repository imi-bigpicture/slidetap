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

"""Metas controller."""
from abc import ABCMeta
from http import HTTPStatus

from flask import Blueprint, Response, jsonify, make_response
from flask.wrappers import Response as FlaskResponse
from slidetap.web.services import LoginService


class Controller(metaclass=ABCMeta):
    """Metaclass for a controller."""

    def __init__(self, login_service: LoginService, blueprint: Blueprint):
        """Create a base controller.

        Parameters
        ----------
        login_service: LoginService
            Service handling user login state.
        blueprint: Blueprin
            The blueprint for the controller.
        """
        self._login_service = login_service
        self._blueprint = blueprint

    @property
    def blueprint(self) -> Blueprint:
        """Return the blueprint for the controller."""
        return self._blueprint

    @property
    def login_service(self) -> LoginService:
        """Return the login service for the controller."""
        return self._login_service

    def return_json(self, item: object) -> Response:
        return jsonify(item)

    def return_not_found(self) -> Response:
        return make_response("", HTTPStatus.NOT_FOUND)

    def return_bad_request(self) -> Response:
        return make_response("", HTTPStatus.BAD_REQUEST)

    def return_ok(self) -> Response:
        return make_response()

    def return_image(self, image: bytes, mimetype: str) -> Response:
        return make_response(image, HTTPStatus.OK, {"Content-Type": mimetype})


class SecuredController(Controller):
    """Controller that requires the user to have a valid session."""

    def __init__(self, login_service: LoginService, blueprint: Blueprint):
        super().__init__(login_service, blueprint)

        @self.blueprint.before_request
        @self.login_service.validate_auth()
        def validate_auth():
            pass

        @self.blueprint.after_request
        # @self.login_service.validate_auth()
        def refresh(response: FlaskResponse) -> FlaskResponse:
            """Refresh user."""
            try:
                return self.login_service.refresh(response)
            except (RuntimeError, KeyError):
                return response
