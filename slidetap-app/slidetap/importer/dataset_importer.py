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

from abc import ABCMeta, abstractmethod
from typing import Iterable, Optional

from flask import Flask

from slidetap.flask_extension import FlaskExtension
from slidetap.model.dataset import Dataset, ImportableDataset
from slidetap.task.scheduler import Scheduler


class DatasetImporter(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for dataset importer."""

    def __init__(self, scheduler: Scheduler, app: Optional[Flask] = None):
        self._scheduler = scheduler
        super().__init__(app)

    @abstractmethod
    def get_importable_datasets(self) -> Iterable[ImportableDataset]:
        """Should return a selection of importable datasets"""
        raise NotImplementedError()

    @abstractmethod
    def import_dataset(self, dataset: Dataset):
        """Should import a dataset."""
        raise NotImplementedError()


class BackgroundDatasetImporter(DatasetImporter):
    def __init__(
        self,
        scheduler: Scheduler,
        app: Optional[Flask] = None,
    ):
        super().__init__(scheduler, app)

    def get_importable_datasets(self) -> Iterable[ImportableDataset]:
        return self._get_importable_datasets()

    def import_dataset(self, dataset: ImportableDataset):
        """Search for metadata for project with defined parameters from file."""
        if dataset not in self._get_importable_datasets():
            raise ValueError(f"Dataset {dataset} is not importable")
        self._scheduler.dataset_import(dataset.path)

    @abstractmethod
    def _get_importable_datasets(
        self,
    ) -> Iterable[ImportableDataset]:
        raise NotImplementedError()
