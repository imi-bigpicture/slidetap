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

"""Meta login controller."""

from abc import ABCMeta

from flask import Blueprint

from slidetap.controller.controller import Controller
from slidetap.services import LoginService


class LoginController(Controller, metaclass=ABCMeta):
    def __init__(self, login_service: LoginService):
        super().__init__(login_service, Blueprint("login", __name__))
