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
