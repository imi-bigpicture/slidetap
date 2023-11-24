"""Module with controllers using Flask blueprints."""

from slidetap.controller.attribute_controller import AttributeController
from slidetap.controller.controller import Controller
from slidetap.controller.image_controller import ImageController
from slidetap.controller.item_controller import ItemController
from slidetap.controller.login import (
    BasicAuthLoginController,
    LoginController,
    OauthAuthLoginController,
)
from slidetap.controller.mapper_controller import MapperController
from slidetap.controller.project_controller import ProjectController
