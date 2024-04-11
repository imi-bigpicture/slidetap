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

from typing import Union
from uuid import uuid4

from werkzeug.datastructures import FileStorage

from slidetap.database import Project, ProjectSchema, Schema
from slidetap.importer import MetadataImporter
from slidetap.model import Session
from slidetap.scheduler import Scheduler


class DummyMetadataImporter(MetadataImporter):
    def __init__(self, scheduler: Scheduler):
        super().__init__(scheduler)
        self._schema = Schema(uuid4(), "test schema")

    def create_project(self, session: Session, name: str) -> Project:
        project_schema = ProjectSchema.get_for_schema(self.schema)
        return Project(name, project_schema)

    def search(self, user: str, project: Project, file: Union[FileStorage, bytes]):
        pass

    @property
    def schema(self) -> Schema:
        return self._schema
