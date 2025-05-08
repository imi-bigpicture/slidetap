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
from typing import Generic, Iterable, TypeVar
from uuid import UUID

from werkzeug.datastructures import FileStorage

from slidetap.model import Batch, Dataset, Image, Item, Project

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
    - search: Search for and create metadata using search parameters.
    - import_image_metadata: Parse metadata for image.
    """

    @abstractmethod
    def parse_file(self, file: FileStorage) -> MetadataSearchParameterType:
        """
        Parse the file and return a metadata search parameters.

        Parameters
        ----------
        file: FileStorage
            The file to parse.
        """

        raise NotImplementedError()

    @abstractmethod
    def create_project(self, name: str, dataset_uid: UUID) -> Project:
        """
        Create a project.

        Parameters
        ----------
        name: str
            The name of the project.
        dataset_uid: UUID
            The UID of the dataset to items in the project should belongs to.
        """
        raise NotImplementedError()

    @abstractmethod
    def create_dataset(self, name: str) -> Dataset:
        """
        Create a dataset.

        Parameters
        ----------
        name: str
            The name of the dataset.
        """
        raise NotImplementedError()

    @abstractmethod
    def search(
        self,
        batch: Batch,
        dataset: Dataset,
        search_parameters: MetadataSearchParameterType,
    ) -> Iterable[Item]:
        """
        Search for metada using search parameters and yield created items.

        Must throw an exception if the metadata cannot be imported.

        Parameters
        ----------
        batch: Batch
            The batch to search in.
        dataset: Dataset
            The dataset to search in.
        search_parameters: MetadataSearchParameterType
            The search parameters to use for the search.
        Returns
        -------
        Iterable[Item]
            The items created from the search.
        """
        raise NotImplementedError()

    @abstractmethod
    def import_image_metadata(
        self, image: Image, batch: Batch, project: Project
    ) -> Image:
        """Parse metadata for image.

        Parameters
        ----------
        image: Image
            The image to parse metadata for.
        batch: Batch
            The batch to which the image belongs.
        project: Project
            The project to which the image belongs.

        Returns
        -------
        Image
            The image with parsed metadata.
        """
        raise NotImplementedError()
