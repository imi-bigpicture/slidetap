"""Meta login controller."""

from abc import ABCMeta

from flask import Blueprint

from slidetap.controller.controller import Controller
from slidetap.services import LoginService


class LoginController(Controller, metaclass=ABCMeta):
    def __init__(self, login_service: LoginService):
        super().__init__(login_service, Blueprint("login", __name__))
