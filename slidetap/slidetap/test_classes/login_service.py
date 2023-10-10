from functools import wraps
from http import HTTPStatus

from flask import make_response
from flask.wrappers import Response as FlaskResponse

from slidetap.services import LoginService
from slidetap.model import Session


class TestLoginService(LoginService):
    def validate_auth(self):
        def wrapper(fn):
            @wraps(fn)
            def decorator(*args, **kwargs) -> FlaskResponse:
                return fn(*args, **kwargs)

            return decorator

        return wrapper

    def get_current_user(self) -> str:
        """Return username of current user."""
        return "test user"

    def get_current_session(self) -> Session:
        return Session("test user", "token")

    def login(self, session: Session) -> FlaskResponse:
        return make_response("", HTTPStatus.OK)

    def logout(self) -> FlaskResponse:
        return make_response("", HTTPStatus.OK)

    def refresh(self, response: FlaskResponse) -> FlaskResponse:
        return response
