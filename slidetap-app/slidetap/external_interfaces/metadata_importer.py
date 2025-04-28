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

import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID

from flask import Blueprint
from werkzeug.datastructures import FileStorage

from slidetap.external_interfaces.fileparser import CaseIdFileParser
from slidetap.model.batch import Batch
from slidetap.model.dataset import Dataset
from slidetap.model.project import Project
from slidetap.task.scheduler import Scheduler


class MetadataImporter(metaclass=ABCMeta):
    """Metaclass for metadata importer."""

    @property
    def blueprint(self) -> Optional[Blueprint]:
        """If importer have api endpoints they should be register
        to a blueprint and returned using this property."""
        return None

    def reset_batch(self, batch: Batch):
        """Should reset any internally stored data for project."""
        pass

    @abstractmethod
    def create_project(self, name: str, dataset_uid: UUID) -> Project:
        """Should create a new project and return it."""
        raise NotImplementedError()

    @abstractmethod
    def create_dataset(self, name: str) -> Dataset:
        """Should create a new dataset for the project and return it."""
        raise NotImplementedError()

    @abstractmethod
    def search(
        self,
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
            logging.error(
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
    def __init__(self, scheduler: Scheduler):
        self._scheduler = scheduler

    def search(
        self,
        dataset: Dataset,
        batch: Batch,
        file: FileStorage,
    ):
        """Search for metadata for project with defined parameters from file."""
        logging.info(f"Searching for metadata for batch {batch.uid}.")
        try:
            search_parameters = self._get_search_parameters(file)
        except Exception as exception:
            logging.error(
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
        scheduler: Scheduler,
        search_parameter_parser: SearchParameterParser,
    ):
        self._search_parameter_parser = search_parameter_parser
        super().__init__(scheduler)

    def search(
        self,
        dataset: Dataset,
        batch: Batch,
        file: FileStorage,
    ):
        """Search for metadata for project with defined parameters from file."""
        logging.info(f"Searching for metadata for batch {batch.uid}.")
        try:
            search_parameters = self._search_parameter_parser.parse(file)
        except Exception as exception:
            logging.error(
                f"Failed to parse file for batch {batch.uid}",
                exc_info=True,
            )
            raise exception
        self._scheduler.metadata_batch_import(batch, **search_parameters)

    def _get_search_parameters(self, file: FileStorage) -> Dict[str, Any]:
        return self._search_parameter_parser.parse(file)
