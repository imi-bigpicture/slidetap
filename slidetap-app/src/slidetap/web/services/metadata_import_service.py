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

"""Metaclass for metadata importer."""

from typing import BinaryIO, Optional
from uuid import UUID

from slidetap.external_interfaces import MetadataImportInterface
from slidetap.model import Batch, Dataset, Project, File
from slidetap.services import BatchService, DatabaseService, SchemaService
from slidetap.task import Scheduler


class MetadataImportService:
    def __init__(
        self,
        scheduler: Scheduler,
        batch_service: BatchService,
        database_service: DatabaseService,
        schema_service: SchemaService,
        metadata_import_interface: MetadataImportInterface,
    ):
        self._scheduler = scheduler
        self._batch_service = batch_service
        self._database_service = database_service
        self._schema_service = schema_service
        self._metadata_import_interface = metadata_import_interface

    def create_project(self, name: str, dataset_uid: UUID) -> Project:
        return self._metadata_import_interface.create_project(name, dataset_uid)

    def create_dataset(self, name: str) -> Dataset:
        return self._metadata_import_interface.create_dataset(name)

    def search(
        self, batch_uid: UUID, file: File
    ) -> Optional[Batch]:
        """Start metadata search for a batch using uploaded file."""
        with self._database_service.get_session() as session:
            database_batch = self._database_service.get_batch(
                session,
                batch_uid,
            )
            self._batch_service.reset(database_batch, session)
            for item_schema in self._schema_service.items.values():
                self._database_service.delete_items(
                    session,
                    item_schema,
                    batch_uid,
                )
            batch = self._batch_service.set_as_searching(database_batch, session)
            # dataset = database_batch.project.dataset.model
            session.commit()
        search_parameters = self._metadata_import_interface.parse_file(
            file
        )
        self._scheduler.metadata_batch_import(
            batch, search_parameters=search_parameters
        )
        return batch
