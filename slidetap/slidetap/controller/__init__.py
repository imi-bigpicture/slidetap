"""Module with controllers using Flask blueprints."""

from slidetap.controller.controller import Controller
from slidetap.controller.mapper_controller import MapperController
from slidetap.controller.project_controller import ProjectController
from slidetap.controller.login import (
    LoginController,
    BasicAuthLoginController,
    OauthAuthLoginController,
)

from slidetap.controller.image_controller import ImageController
