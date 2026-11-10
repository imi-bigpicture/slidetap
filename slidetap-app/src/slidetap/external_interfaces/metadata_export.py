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
from uuid import UUID

from slidetap.model import (
    Batch,
    Dataset,
    ExportNotice,
    ExportPreviewFile,
    Item,
    Project,
)


class MetadataExportInterface(metaclass=ABCMeta):
    """
    Metaclass for interface for exporting metadata. Implementations must implement:
    - preview_item: Return a serialized representation of the item.
    - export: Serialize all metadata for the project to storage.

    And may implement `preview_export`, to show what the export writes for an
    item together with everything connected to it, and `batch_export_refusal`,
    `batch_shared_items` and `export_batch`, to export a batch on its own, see
    :py:attr:`ApplicationPolicy.allows_batch_export`.
    """

    @abstractmethod
    def preview_item(self, item: Item) -> str | None:
        """
        Return a serialized representation of the item.

        Parameters
        ----------
        item: Item
            The item to serialize.
        """
        raise NotImplementedError()

    def preview_export(self, item: Item) -> list[ExportPreviewFile]:
        """
        What the export writes for the item and everything connected to it, such
        as a case with its samples, images and observations, as one entry per
        file the export writes them to. Empty where nothing is written.

        The default is the preview of the item alone, as one file named by the
        item's identifier.

        Parameters
        ----------
        item: Item
            The item to preview.
        """
        preview = self.preview_item(item)
        if preview is None:
            return []
        return [ExportPreviewFile(name=item.identifier, content=preview)]

    def export_notices(self, item: Item) -> list[ExportNotice]:
        """
        What a curator should know about how the item is exported, where it is
        exported otherwise than it is stored, such as a case exported as several:
        one notice for each way it is. Empty where there is nothing to say, which
        is the default.

        Parameters
        ----------
        item: Item
            The item to tell about.
        """
        return []

    @abstractmethod
    def export(self, project: Project, dataset: Dataset) -> None:
        """
        Export metadata for the project to storage.

        Must only export items that are selected. An item that is not selected is
        not part of the dataset: it is not stored to the outbox, and exporting
        metadata for it would describe an image that is not there. An image that
        cannot be stored is excluded from the dataset by deselecting it, which is
        what lets the batch it belongs to be completed.

        Metadata is exported for a project once all its batches are completed, and
        thus once every image it stores has been stored to the outbox, or excluded.

        Must throw an exception if the metadata cannot be exported.

        Parameters
        ----------
        project: Project
            The project to export metadata for.
        dataset: Dataset
            The dataset to export metadata for.
        """
        raise NotImplementedError()

    def batch_export_refusal(self, batch: Batch) -> str | None:
        """
        Why the batch cannot be exported on its own, None if it can.

        A batch exported on its own is handed over before the rest of its
        project and cannot be taken back, so its export must not depend on
        anything outside it that can change or is exported later, such as an
        item of it with something from another batch under it.

        Asked before the batch's images are stored and again before its metadata
        is exported. The default refuses every batch; override this and
        `export_batch` to support it.

        Parameters
        ----------
        batch: Batch
            The batch to export on its own.
        """
        return "The metadata export does not export a batch on its own."

    def batch_shared_items(self, batch: Batch) -> list[UUID]:
        """
        Items of other batches the batch is exported with, such as the
        biological being a case of it is from. Empty by default.

        They are moved into the batch and locked when it is stored, so its
        export cannot change afterwards.

        Parameters
        ----------
        batch: Batch
            The batch to export on its own.
        """
        return []

    def export_batch(self, project: Project, dataset: Dataset, batch: Batch) -> None:
        """
        Export the metadata of a batch exported on its own into its bundle.

        As `export`, but only for the batch and its `batch_shared_items`. Its
        images are already in its bundle, see `StorageService.project_bundle`;
        its metadata and pseudonyms go there too.

        Must throw an exception if the metadata cannot be exported.

        Parameters
        ----------
        project: Project
            The project the batch is of.
        dataset: Dataset
            The dataset of the project.
        batch: Batch
            The batch to export metadata for.
        """
        raise NotImplementedError()
