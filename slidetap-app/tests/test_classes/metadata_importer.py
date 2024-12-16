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

from slidetap.database import DatabaseProject
from slidetap.model import UserSession
from slidetap.model.project import Project
from slidetap.model.schema.root_schema import RootSchema
from slidetap.task.scheduler import Scheduler
from slidetap.web.importer import MetadataImporter
from werkzeug.datastructures import FileStorage


class DummyMetadataImporter(MetadataImporter):
    def __init__(self, root_schema: RootSchema, scheduler: Scheduler):
        super().__init__(root_schema, scheduler)

    def create_project(self, session: UserSession, name: str) -> Project:
        return Project(uuid4(), "test project", self.schema.uid)

    def search(
        self, user: str, project: DatabaseProject, file: Union[FileStorage, bytes]
    ):
        pass
