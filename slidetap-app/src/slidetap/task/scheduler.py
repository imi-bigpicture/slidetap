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

"""Module with schedulers used for calling execution of defined background tasks."""

import logging
from typing import Any
from uuid import UUID

from celery import group

from slidetap.model import Batch, Image, ImageSchema, Project
from slidetap.services import DatabaseService
from slidetap.task.tasks import (
    download_and_pre_process_image,
    post_process_image,
    process_metadata_export,
    process_metadata_import,
    remap_batch_attributes,
    remap_dataset_attributes,
    retry_metadata_search_item,
    store_batch_images_to_outbox,
)


class Scheduler:
    """Interface for starting celery tasks."""

    def __init__(self, database_service: DatabaseService):
        self._database_service = database_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def pre_process_images_in_batch(self, batch: Batch, image_schema: ImageSchema):
        """Pre-process images in batch."""
        try:
            image_uids = self._image_uids_in_batch(batch, image_schema)
            if not image_uids:
                return
            group(
                download_and_pre_process_image.si(uid)  # type: ignore
                for uid in image_uids
            ).apply_async()
        except Exception:
            self._logger.error(
                f"Error downloading and pre-processing images of schema {image_schema} for batch {batch.uid}",
                exc_info=True,
            )

    def download_and_pre_process_image(self, image: Image):
        self._logger.info(f"Downloading and pre-processing image {image.uid}")
        try:
            download_and_pre_process_image.delay(image.uid)  # type: ignore
        except Exception:
            self._logger.error(
                f"Error downloading and pre-processing image {image.uid}", exc_info=True
            )

    def post_process_images_in_batch(self, batch: Batch, image_schema: ImageSchema):
        """Post-process images in batch."""
        try:
            image_uids = self._image_uids_in_batch(batch, image_schema)
            if not image_uids:
                return
            group(
                post_process_image.si(uid) for uid in image_uids  # type: ignore
            ).apply_async()
        except Exception:
            self._logger.error(
                f"Error post-processing images for batch {batch.uid}", exc_info=True
            )

    def _image_uids_in_batch(
        self, batch: Batch, image_schema: ImageSchema
    ) -> list[UUID]:
        with self._database_service.get_session(commit=False) as session:
            images = self._database_service.get_images(
                session, schema=image_schema, batch=batch.uid
            )
            return [image.uid for image in images]

    def post_process_image(self, image: Image):
        self._logger.info(f"Post processing image {image.uid}")
        try:
            post_process_image.delay(image.uid)  # type: ignore
        except Exception:
            self._logger.error(
                f"Error post-processing image {image.uid}", exc_info=True
            )

    def metadata_project_export(self, project: Project):
        self._logger.info(f"Exporting metadata for project {project.uid}")
        try:
            process_metadata_export.delay(project.uid)  # type: ignore
        except Exception:
            self._logger.error(
                f"Error exporting metadata for project {project.uid}", exc_info=True
            )

    def retry_post_processing_in_batch(self, batch: Batch, image_schema: ImageSchema):
        """Re-submit post-processing for a batch.

        Images that are not stuck will be skipped by the task's entry guard.
        """
        self.post_process_images_in_batch(batch, image_schema)

    def store_images_in_batch(self, batch: Batch):
        """Schedule storing of post-processed images to the outbox."""
        self._logger.info(f"Storing images for batch {batch.uid}")
        try:
            store_batch_images_to_outbox.delay(batch.uid)  # type: ignore
        except Exception:
            self._logger.error(
                f"Error storing images for batch {batch.uid}", exc_info=True
            )

    def metadata_batch_import(self, batch: Batch, search_parameters: Any):
        self._logger.info(f"Importing metadata for batch {batch.uid}: {batch.name}")
        try:
            process_metadata_import.delay(batch.uid, search_parameters)  # type: ignore
        except Exception:
            self._logger.error(
                f"Error importing metadata for batch {batch.uid}: {batch.name}",
                exc_info=True,
            )

    def metadata_retry_search_item(self, search_item_uid: UUID):
        """Schedule retry for a single previously-failed metadata search item."""
        self._logger.info(f"Retrying metadata search item {search_item_uid}")
        try:
            retry_metadata_search_item.delay(search_item_uid)  # type: ignore
        except Exception:
            self._logger.error(
                f"Error scheduling retry for search item {search_item_uid}",
                exc_info=True,
            )

    def remap_batch_attributes(self, batch_uid: UUID):
        """Schedule a remap of every attribute in a batch."""
        self._logger.info(f"Remapping attributes in batch {batch_uid}")
        try:
            remap_batch_attributes.delay(batch_uid)  # type: ignore
        except Exception:
            self._logger.error(
                f"Error scheduling remap for batch {batch_uid}", exc_info=True
            )

    def remap_dataset_attributes(self, dataset_uid: UUID):
        """Schedule a remap of every attribute in a dataset."""
        self._logger.info(f"Remapping attributes in dataset {dataset_uid}")
        try:
            remap_dataset_attributes.delay(dataset_uid)  # type: ignore
        except Exception:
            self._logger.error(
                f"Error scheduling remap for dataset {dataset_uid}", exc_info=True
            )
