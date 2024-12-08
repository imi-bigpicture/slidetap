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

from slidetap.database import DatabaseProject, DatabaseProjectSchema, DatabaseRootSchema
from slidetap.model import UserSession
from slidetap.task.scheduler import Scheduler
from slidetap.web.importer import MetadataImporter
from werkzeug.datastructures import FileStorage


class DummyMetadataImporter(MetadataImporter):
    def __init__(self, scheduler: Scheduler):
        super().__init__(scheduler)
        self._schema = DatabaseRootSchema(uuid4(), "test schema")

    def create_project(self, session: UserSession, name: str) -> DatabaseProject:
        project_schema = DatabaseProjectSchema.get_for_schema(self.schema)
        return DatabaseProject(name, project_schema)

    def search(
        self, user: str, project: DatabaseProject, file: Union[FileStorage, bytes]
    ):
        pass

    @property
    def schema(self) -> DatabaseRootSchema:
        return self._schema
