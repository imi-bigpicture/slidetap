"""Metas controller."""
from abc import ABCMeta
from http import HTTPStatus
from typing import Optional

from flask import Blueprint, Response, current_app, jsonify, make_response
from flask.wrappers import Response as FlaskResponse

from slidetap.services import LoginService


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

        @self.blueprint.after_request
        # TODO
        # @self.login_service.validate_auth()
        def refresh(response: FlaskResponse) -> FlaskResponse:
            """Refresh user."""
            # current_app.logger.debug("Refresh token.")
            try:
                return self.login_service.refresh(response)
            except (RuntimeError, KeyError):
                return response

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
