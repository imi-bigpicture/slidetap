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

"""Importer for json metadata using defined models."""

from typing import Any, Dict, Mapping

from flask import Flask
from slidetap.apps.example.model import ContainerModel
from slidetap.apps.example.schema import ExampleSchema
from slidetap.database.attribute import StringAttribute
from slidetap.database.project import Project
from slidetap.database.schema import Schema
from slidetap.database.schema.attribute_schema import StringAttributeSchema
from slidetap.database.schema.project_schema import ProjectSchema
from slidetap.model import UserSession
from slidetap.web.importer.metadata_importer import (
    BackgroundMetadataImporter,
)
from werkzeug.datastructures import FileStorage


class ExampleMetadataImporter(BackgroundMetadataImporter):
    def init_app(self, app: Flask):
        super().init_app(app)
        with app.app_context():
            self._schema = ExampleSchema.create()

    @property
    def schema(self) -> Schema:
        schema = Schema.get(ExampleSchema.uid)
        assert schema is not None
        return schema

    def create_project(self, session: UserSession, name: str) -> Project:
        schema = ProjectSchema.get_for_schema(self.schema)
        submitter_schema = StringAttributeSchema.get(self.schema, "submitter")
        submitter = StringAttribute(submitter_schema, "test")
        return Project(name, schema, attributes=[submitter])

    def _get_search_parameters(self, file: FileStorage) -> Dict[str, Any]:
        if isinstance(file, FileStorage):
            input = file.stream.read().decode()
        else:
            with open(file, "r") as input_file:
                input = input_file.read()

        container = ContainerModel().loads(input)
        assert isinstance(container, Mapping)
        return {"container": container}
