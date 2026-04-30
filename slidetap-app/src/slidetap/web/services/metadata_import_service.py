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

from typing import List
from uuid import UUID

from slidetap.external_interfaces import (
    MetadataImportInterface,
    MetadataSearchParameterType,
)
from slidetap.model import (
    Batch,
    Dataset,
    File,
    MetadataImportStatus,
    MetadataSearchItem,
    Project,
)
from slidetap.services import (
    BatchService,
    DatabaseService,
    MetadataSearchItemService,
    SchemaService,
)
from slidetap.task import Scheduler


class MetadataImportService:
    def __init__(
        self,
        scheduler: Scheduler,
        batch_service: BatchService,
        database_service: DatabaseService,
        schema_service: SchemaService,
        search_item_service: MetadataSearchItemService,
        metadata_import_interface: MetadataImportInterface[MetadataSearchParameterType],
    ):
        self._scheduler = scheduler
        self._batch_service = batch_service
        self._database_service = database_service
        self._schema_service = schema_service
        self._search_item_service = search_item_service
        self._metadata_import_interface = metadata_import_interface

    @property
    def supports_retry(self) -> bool:
        return self._metadata_import_interface.supports_retry

    def create_project(self, name: str, dataset_uid: UUID) -> Project:
        return self._metadata_import_interface.create_project(name, dataset_uid)

    def create_dataset(self, name: str) -> Dataset:
        return self._metadata_import_interface.create_dataset(name)

    def search(self, batch_uid: UUID, file: File) -> Batch:
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
            self._search_item_service.clear_for_batch(batch_uid, session=session)
            batch = self._batch_service.set_as_searching(database_batch, session)
            session.commit()
        search_parameters = self._metadata_import_interface.parse_file(file)
        self._scheduler.metadata_batch_import(
            batch, search_parameters=search_parameters
        )
        return batch

    def list_search_items(self, batch_uid: UUID) -> List[MetadataSearchItem]:
        return self._search_item_service.list_for_batch(batch_uid)

    def retry_search_item(self, search_item_uid: UUID) -> None:
        """Reset a FAILED search item and queue a retry task."""
        if not self._metadata_import_interface.supports_retry:
            raise ValueError("This importer does not support per-item retry.")
        with self._database_service.get_session() as session:
            from slidetap.database import DatabaseMetadataSearchItem

            row = session.get(DatabaseMetadataSearchItem, search_item_uid)
            if row is None:
                raise ValueError(f"Search item {search_item_uid} does not exist.")
            if row.status != MetadataImportStatus.FAILED:
                raise ValueError(
                    f"Search item {search_item_uid} is not in FAILED state "
                    f"(was {row.status.name})."
                )
            batch = self._database_service.get_batch(session, row.batch_uid)
            if batch is not None and batch.metadata_searching:
                raise ValueError(
                    f"Batch {row.batch_uid} is currently searching; "
                    "wait for the bulk search to complete before retrying."
                )
            self._search_item_service.reset_for_retry(search_item_uid, session=session)
            session.commit()
        self._scheduler.metadata_retry_search_item(search_item_uid)

    def exclude_search_item(self, search_item_uid: UUID) -> None:
        """Delete a FAILED search item, removing it from the user's view."""
        self._search_item_service.delete(search_item_uid)
