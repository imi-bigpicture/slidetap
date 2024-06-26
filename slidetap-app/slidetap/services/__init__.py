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

"""Module containing services used by controllers."""
from slidetap.services.attribute_service import AttributeService
from slidetap.services.auth import (
    AuthService,
    AuthServiceException,
    BasicAuthService,
    OauthAuthService,
    OpenIdAuthService,
)
from slidetap.services.image_service import ImageService
from slidetap.services.login import JwtLoginService, LoginService
from slidetap.services.mapper_service import MapperService
from slidetap.services.project_service import ProjectService
from slidetap.services.schema_service import SchemaService
from slidetap.services.item_service import ItemService
