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
from uuid import UUID

from slidetap.database import DatabaseProject
from slidetap.importer import MetadataImporter
from slidetap.model import Batch, Dataset, UserSession
from slidetap.model.schema.root_schema import RootSchema
from slidetap.task.scheduler import Scheduler
from werkzeug.datastructures import FileStorage


class DummyMetadataImporter(MetadataImporter):
    def __init__(self, root_schema: RootSchema, scheduler: Scheduler):
        super().__init__(root_schema, scheduler)

    def create_project(self, session: UserSession, name: str, batch_uid: UUID):
        pass

    def create_dataset(self, session: UserSession, project: DatabaseProject, name: str):
        pass

    def search(
        self, user: str, dataset: Dataset, batch: Batch, file: Union[FileStorage, bytes]
    ):
        pass
