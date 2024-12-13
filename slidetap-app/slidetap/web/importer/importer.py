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

"""Metaclass for importer."""

from abc import ABCMeta
from typing import Optional

from flask import Blueprint, Flask

from slidetap.flask_extension import FlaskExtension
from slidetap.model.project import Project
from slidetap.model.schema.root_schema import RootSchema
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ItemService,
    MapperService,
    ProjectService,
    SchemaService,
    ValidationService,
)
from slidetap.task.scheduler import Scheduler


class Importer(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for importer."""

    def __init__(
        self, root_schema: RootSchema, scheduler: Scheduler, app: Optional[Flask] = None
    ):
        self._root_schema = root_schema
        self._scheduler = scheduler
        super().__init__(app)

    def init_app(self, app: Flask) -> None:
        self._database_service = DatabaseService()
        self._validation_service = ValidationService(self._database_service)
        self._schema_service = SchemaService(self._root_schema)
        self._attribute_service = AttributeService(
            self._schema_service, self._validation_service, self._database_service
        )
        self._mapper_service = MapperService(
            self._validation_service, self._database_service
        )
        self._item_service = ItemService(
            self._attribute_service,
            self._mapper_service,
            self._validation_service,
            self._database_service,
        )
        self._project_service = ProjectService(
            self._attribute_service, self._database_service
        )

    @property
    def blueprint(self) -> Optional[Blueprint]:
        """If importer have api endpoints they should be register
        to a blueprint and returned using this property."""
        return None

    def reset_project(self, project: Project):
        """Should reset any internally stored data for project."""
        pass
