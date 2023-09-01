"""Module with controllers using Flask blueprints."""

from slides.controller.controller import Controller
from slides.controller.mapper_controller import MapperController
from slides.controller.project_controller import ProjectController
from slides.controller.login import (
    LoginController,
    BasicAuthLoginController,
    OauthAuthLoginController,
)

from slides.controller.image_controller import ImageController
