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

from uuid import UUID

from fastapi import UploadFile

from slidetap.external_interfaces import MetadataImportInterface
from slidetap.model import Batch, Dataset, Project
from slidetap.task import Scheduler


class MetadataImportService:
    def __init__(
        self, scheduler: Scheduler, metadata_import_interface: MetadataImportInterface
    ):
        self._scheduler = scheduler
        self._metadata_import_interface = metadata_import_interface

    def create_project(self, name: str, dataset_uid: UUID) -> Project:
        return self._metadata_import_interface.create_project(name, dataset_uid)

    def create_dataset(self, name: str) -> Dataset:
        return self._metadata_import_interface.create_dataset(name)

    def search(
        self,
        dataset: Dataset,
        batch: Batch,
        file: UploadFile,
    ):
        search_parameters = self._metadata_import_interface.parse_file(file)
        self._scheduler.metadata_batch_import(
            batch, search_parameters=search_parameters
        )
