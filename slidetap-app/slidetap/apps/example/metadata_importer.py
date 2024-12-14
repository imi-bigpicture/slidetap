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
from uuid import uuid4

from slidetap.apps.example.model import ContainerModel
from slidetap.database import DatabaseProject
from slidetap.model import Project, UserSession
from slidetap.model.attribute import StringAttribute
from slidetap.model.project_status import ProjectStatus
from slidetap.model.schema.root_schema import RootSchema
from slidetap.web.importer.metadata_importer import (
    BackgroundMetadataImporter,
)
from werkzeug.datastructures import FileStorage


class ExampleMetadataImporter(BackgroundMetadataImporter):

    @property
    def schema(self) -> RootSchema:
        return self._root_schema

    def create_project(self, session: UserSession, name: str) -> Project:
        submitter_schema = self._schema_service.project.attributes["submitter"]
        project = Project(
            uuid4(),
            name,
            ProjectStatus.INITIALIZED,
            True,
            self.schema.project.uid,
            attributes={
                submitter_schema.tag: StringAttribute(
                    uuid4(),
                    submitter_schema.uid,
                    "test",
                )
            },
        )
        return DatabaseProject.get_or_create_from_model(
            project, self._schema_service.project
        ).model

    def _get_search_parameters(self, file: FileStorage) -> Dict[str, Any]:
        if isinstance(file, FileStorage):
            input = file.stream.read().decode()
        else:
            with open(file, "r") as input_file:
                input = input_file.read()

        container = ContainerModel().loads(input)
        assert isinstance(container, Mapping)
        return {"container": container}
