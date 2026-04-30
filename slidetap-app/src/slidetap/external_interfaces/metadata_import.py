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

from slidetap.model import (
    Batch,
    Dataset,
    File,
    Image,
    MetadataSearchItem,
    Project,
    MetadataSearchResult,
)

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
    - search: yield one MetadataSearchResult per import unit.
    - import_image_metadata: Parse metadata for image.

    Implementations may override:
    - supports_retry: True if retry_item produces a fresh unit on demand.
    - retry_item: re-run the import for a single previously-failed search item.
    """

    @property
    def supports_retry(self) -> bool:
        """Whether this importer supports per-search-item retry.

        True iff ``retry_item`` is implemented. List/identifier-based
        importers can typically retry by re-running the import for the
        identifier; file-parse importers usually cannot without the
        original file and return False.
        """
        return False

    def retry_item(
        self,
        search_item: MetadataSearchItem,
        batch: Batch,
        dataset: Dataset,
    ) -> MetadataSearchResult:
        """Re-run metadata import for a single previously-failed search item.

        Only called when ``supports_retry`` is True. Returns a fresh
        ``MetadataSearchResult`` with the same identifier as the search item — items
        populated on success, ``failure_message`` set on graceful failure.

        Raise only for hard failures the caller should treat as a
        catastrophic retry error; in that case the search item is re-marked
        FAILED with the exception message.
        """
        raise NotImplementedError()

    @abstractmethod
    def parse_file(self, file: File) -> MetadataSearchParameterType:
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
    ) -> Iterable[MetadataSearchResult]:
        """Search for metadata and yield one MetadataSearchResult per import unit.

        For list-based importers, one unit per input identifier
        (e.g. one per case_id). For per-case file-parse importers, one unit
        per case found in the file. Each yielded unit becomes one row in
        the metadata_search_item table.

        Items within a successful unit must be in dependency order
        (parents before children); the driver persists them per-unit with
        a per-unit commit, so a failed persist isolates to that unit.

        Implementations should dedup their input identifiers — duplicates
        will produce duplicate search-item rows.

        Raise only for batch-level failures (file unparseable up front,
        external system unreachable, etc.) — those are reported as a
        failed batch.

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
        Iterable[MetadataSearchResult]
            One unit per attempt; items populated on success, message set
            on per-unit failure.
        """
        raise NotImplementedError()

    @abstractmethod
    def import_image_metadata(
        self, image: Image, batch: Batch, project: Project, task_id: str
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
        task_id: str
            The Celery task ID, used to isolate processing output per task.

        Returns
        -------
        Image
            The image with parsed metadata.
        """
        raise NotImplementedError()
