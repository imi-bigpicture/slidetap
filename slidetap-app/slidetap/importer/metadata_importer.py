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

from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID

from flask import Flask, current_app
from werkzeug.datastructures import FileStorage

from slidetap.importer.fileparser import CaseIdFileParser
from slidetap.importer.importer import Importer
from slidetap.model import RootSchema, UserSession
from slidetap.model.batch import Batch
from slidetap.model.dataset import Dataset
from slidetap.model.project import Project
from slidetap.task.scheduler import Scheduler


class MetadataImporter(Importer, metaclass=ABCMeta):
    """Metaclass for metadata importer."""

    @abstractmethod
    def create_project(
        self, session: UserSession, name: str, dataset_uid: UUID
    ) -> Project:
        """Should create a new project and return it."""
        raise NotImplementedError()

    @abstractmethod
    def create_dataset(self, session: UserSession, name: str) -> Dataset:
        """Should create a new dataset for the project and return it."""
        raise NotImplementedError()

    @abstractmethod
    def search(
        self,
        session: UserSession,
        dataset: Dataset,
        batch: Batch,
        file: FileStorage,
    ):
        """Should search for metadata based on search criteria defined in
        file, and add found metadata to project."""
        raise NotImplementedError()


class SearchParameterParser(metaclass=ABCMeta):
    @abstractmethod
    def parse(self, file: FileStorage) -> Dict[str, Any]:
        raise NotImplementedError()


class CaseIdSearchParameterParser(SearchParameterParser):
    def parse(self, file: FileStorage):
        try:
            case_ids = CaseIdFileParser(file).caseIds
        except Exception as exception:
            current_app.logger.error(
                "Failed to parse file.",
                exc_info=True,
            )
            raise exception
        return {"case_ids": case_ids}


class ByteSearchParameterParser(SearchParameterParser):
    def parse(self, file: FileStorage):
        with file.stream as stream:
            return {"file": stream.read()}


class BackgroundMetadataImporter(MetadataImporter):
    def search(
        self,
        session: UserSession,
        dataset: Dataset,
        batch: Batch,
        file: FileStorage,
    ):
        """Search for metadata for project with defined parameters from file."""
        current_app.logger.info(f"Searching for metadata for batch {batch.uid}.")
        try:
            search_parameters = self._get_search_parameters(file)
        except Exception as exception:
            current_app.logger.error(
                f"Failed to parse file for batch {batch.uid}",
                exc_info=True,
            )
            raise exception
        self._scheduler.metadata_batch_import(batch, **search_parameters)

    @abstractmethod
    def _get_search_parameters(self, file: FileStorage) -> Dict[str, Any]:
        raise NotImplementedError()


class SearchParameterMetadataImporter(BackgroundMetadataImporter):

    def __init__(
        self,
        root_schema: RootSchema,
        scheduler: Scheduler,
        search_parameter_parser: SearchParameterParser,
        app: Optional[Flask] = None,
    ):
        self._search_parameter_parser = search_parameter_parser
        super().__init__(root_schema, scheduler, app)

    def search(
        self,
        session: UserSession,
        dataset: Dataset,
        batch: Batch,
        file: FileStorage,
    ):
        """Search for metadata for project with defined parameters from file."""
        current_app.logger.info(f"Searching for metadata for batch {batch.uid}.")
        try:
            search_parameters = self._search_parameter_parser.parse(file)
        except Exception as exception:
            current_app.logger.error(
                f"Failed to parse file for batch {batch.uid}",
                exc_info=True,
            )
            raise exception
        self._scheduler.metadata_batch_import(batch, **search_parameters)

    def _get_search_parameters(self, file: FileStorage) -> Dict[str, Any]:
        return self._search_parameter_parser.parse(file)
