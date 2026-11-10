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

"""Metaclass for metadata exporter."""

import logging
from uuid import UUID

from slidetap.application_policy import ApplicationPolicy
from slidetap.external_interfaces import MetadataExportInterface
from slidetap.model import (
    Batch,
    ExportNotice,
    ExportPreviewFile,
    NotAllowedActionError,
    Project,
)
from slidetap.services import (
    BatchService,
    ItemService,
    ProjectService,
    SchemaService,
)
from slidetap.services.database_service import DatabaseService
from slidetap.task import Scheduler


class MetadataExportService:
    def __init__(
        self,
        scheduler: Scheduler,
        project_service: ProjectService,
        batch_service: BatchService,
        item_service: ItemService,
        database_service: DatabaseService,
        schema_service: SchemaService,
        metadata_export_interface: MetadataExportInterface,
        application_policy: ApplicationPolicy,
    ):
        self._application_policy = application_policy
        self._scheduler = scheduler
        self._project_service = project_service
        self._batch_service = batch_service
        self._item_service = item_service
        self._database_service = database_service
        self._schema_service = schema_service
        self._metadata_export_interface = metadata_export_interface
        self._logger = logging.getLogger(__name__)

    def export(self, project: Project):
        """Set the project as exporting and queue the export of its metadata.

        An export that cannot be queued sets the project back as completed,
        rather than leave it exporting with nothing exporting it, and raises.
        """
        self._logger.info(f"Exporting project {project}.")
        self._schema_service.assert_can_change(project)
        self._project_service.set_as_exporting(project)
        try:
            self._scheduler.metadata_project_export(project)
        except Exception:
            self._logger.error(
                f"Failed to queue export of project {project.uid}", exc_info=True
            )
            self._project_service.revert_export(project.uid)
            raise

    def store_batch(self, batch_uid: UUID) -> Batch:
        """Start storing the images of a locked batch into a bundle of its own,
        and queue it.

        Step one of two; `export_batch` then exports the metadata. After this the
        batch cannot be reopened. A batch already storing is queued again, which
        resumes a failed store, and is left storing if queueing fails.

        Raises
        ------
        NotAllowedActionError
            If the batch cannot be exported on its own, see
            `MetadataExportInterface.batch_export_refusal` and
            `BatchService.set_as_storing_alone`.
        """
        batch = self._batch_service.get(batch_uid)
        self._assert_can_export_alone(batch)
        stored = self._batch_service.set_as_storing_alone(
            batch.uid, self._metadata_export_interface.batch_shared_items(batch)
        )
        self._logger.info(f"Storing batch {batch_uid} on its own.")
        self._scheduler.store_images_in_batch(stored)
        return stored

    def export_batch(self, batch_uid: UUID) -> Batch:
        """Set a batch stored on its own as exporting, and queue the export of
        its metadata into its bundle.

        If queueing fails, the batch is set back to completed and the error
        raised.

        Raises
        ------
        NotAllowedActionError
            If the batch cannot be exported on its own, or is not wholly stored.
        """
        batch = self._batch_service.get(batch_uid)
        self._assert_can_export_alone(batch)
        exporting = self._batch_service.set_as_exporting(batch.uid)
        try:
            self._scheduler.metadata_batch_export(exporting)
        except Exception as exception:
            self._logger.error(
                f"Failed to queue export of batch {batch_uid}", exc_info=True
            )
            self._batch_service.revert_export(
                batch_uid, message=f"Export could not be queued: {exception}"
            )
            raise
        return exporting

    def _assert_can_export_alone(self, batch: Batch) -> None:
        """Refuse the batch if batch export is not allowed, the export refuses
        it, the project's seed is cleared, or an item has no pseudonym."""
        if not self._application_policy.allows_batch_export:
            raise NotAllowedActionError(
                "This application does not export a batch on its own."
            )
        refusal = self._metadata_export_interface.batch_export_refusal(batch)
        if refusal is not None:
            raise NotAllowedActionError(refusal)
        project = self._project_service.get(batch.project_uid)
        # Raises if the seed is cleared: what the export derives from it could
        # not be reproduced.
        self._project_service.get_export_seed(project.dataset_uid)
        missing = self._item_service.items_missing_pseudonym(
            project.dataset_uid, batch_uid=batch.uid
        )
        if missing > 0:
            raise NotAllowedActionError(
                f"{missing} items of batch {batch.name} have no pseudonym, and "
                "cannot be named in its bundle."
            )

    def preview_item(self, item_uid: UUID) -> str | None:
        """A preview of the item as it would be exported, None where the
        project cannot be changed."""
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            if not self._schema_service.can_change(item, session):
                return None
            return self._metadata_export_interface.preview_item(item.model)

    def preview_export(self, item_uid: UUID) -> list[ExportPreviewFile]:
        """What the export writes for the item and everything connected to it,
        file by file. Empty where the project cannot be changed, as for the
        preview."""
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            if not self._schema_service.can_change(item, session):
                return []
            return self._metadata_export_interface.preview_export(item.model)

    def export_notices(self, item_uid: UUID) -> list[ExportNotice]:
        """What to know about how the item is exported, empty where there is
        nothing or the project cannot be changed, as for the preview."""
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            if not self._schema_service.can_change(item, session):
                return []
            return self._metadata_export_interface.export_notices(item.model)
