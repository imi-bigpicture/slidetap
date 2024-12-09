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

from typing import Optional
from uuid import UUID

from flask import Flask

from slidetap.flask_extension import FlaskExtension
from slidetap.services.attribute_service import AttributeService
from slidetap.services.item_service import ItemService
from slidetap.services.mapper_service import MapperService
from slidetap.services.project_service import ProjectService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class Processor(FlaskExtension):
    def __init__(self, root_schema_uid: UUID, app: Optional[Flask] = None) -> None:
        self._root_schema_uid = root_schema_uid
        super().__init__(app)

    def init_app(self, app: Flask) -> None:
        self._validation_service = ValidationService()
        self._schema_service = SchemaService(self._root_schema_uid)
        self._attribute_service = AttributeService(
            self._schema_service, self._validation_service
        )
        self._mapper_service = MapperService(self._validation_service)
        self._item_service = ItemService(
            self._attribute_service, self._mapper_service, self._validation_service,
        )
        self._project_service = ProjectService(self._attribute_service)

        super().init_app(app)
