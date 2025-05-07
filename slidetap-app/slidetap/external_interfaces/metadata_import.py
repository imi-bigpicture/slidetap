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
from typing import Any, Dict, Generic, TypeVar
from uuid import UUID

from werkzeug.datastructures import FileStorage

from slidetap.model.dataset import Dataset
from slidetap.model.project import Project

MetadataSearchParameterType = TypeVar("MetadataSearchParameterType")


class MetadataImportInterface(
    Generic[MetadataSearchParameterType],
    metaclass=ABCMeta,
):
    """
    Metaclass for interface for importing metadata. Implementations must implement:
    - parse_file: Parse a file and return metadata search parameters.
    - create_project: Create a project.
    - create_dataset: Create a dataset.
    - search: Search for and import metadata using search parameters.
    - import_image_metadata: Parse metadata for image.
    """

    @abstractmethod
    def parse_file(self, file: FileStorage) -> MetadataSearchParameterType:
        """Parse the file and return a metadata search parameters."""
        raise NotImplementedError()

    @abstractmethod
    def create_project(self, name: str, dataset_uid: UUID) -> Project:
        """Create a project."""
        raise NotImplementedError()

    @abstractmethod
    def create_dataset(self, name: str) -> Dataset:
        """Create a dataset."""
        raise NotImplementedError()

    @abstractmethod
    def search(
        self,
        batch_uid: UUID,
        search_parameters: MetadataSearchParameterType,
        **kwargs: Dict[str, Any]
    ):
        """Search for and import metadata using search parameters."""
        raise NotImplementedError()

    @abstractmethod
    def import_image_metadata(self, image_uid: UUID, **kwargs: Dict[str, Any]) -> None:
        """Parse image metadata."""
        raise NotImplementedError()
