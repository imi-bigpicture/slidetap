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

"""Public dispatch API for background tasks."""

import logging
from typing import Any, Iterable
from uuid import UUID

from procrastinate import App as TaskApp
from procrastinate.exceptions import AlreadyEnqueued

from slidetap.model import Batch, Image, Project
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
    """Interface for starting background tasks.

    The Procrastinate :class:`App` is expected to be opened for the
    process lifetime (see :class:`SlideTapWebAppFactory`'s lifespan), so
    methods only ``await ...defer_async(...)`` — they do not open or
    close the connector themselves.
    """

    def __init__(self, app: TaskApp):
        self._app = app
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def pre_process_images(self, image_uids: Iterable[UUID]) -> None:
        """Defer pre-processing for each image.

        Each task takes ``lock=f"image-{uid}"`` so at most one task touches
        a given image at a time. Per-image entry guards still apply; the
        lock is an upstream filter that keeps the worker from picking up
        a job whose guard would just bail.
        """
        try:
            for uid in image_uids:
                await download_and_pre_process_image.configure(
                    lock=f"image-{uid}",
                ).defer_async(image_uid=str(uid))
        except Exception:
            self._logger.error(
                "Error deferring pre-process tasks",
                exc_info=True,
            )

    async def download_and_pre_process_image(self, image: Image):
        """Defer pre-processing for one image.

        Same per-image ``lock`` as :meth:`pre_process_images`.
        """
        self._logger.info(f"Downloading and pre-processing image {image.uid}")
        try:
            await download_and_pre_process_image.configure(
                lock=f"image-{image.uid}",
            ).defer_async(image_uid=str(image.uid))
        except Exception:
            self._logger.error(
                f"Error downloading and pre-processing image {image.uid}",
                exc_info=True,
            )

    async def post_process_images(self, image_uids: Iterable[UUID]) -> None:
        """Defer post-processing for each image.

        Each task takes ``lock=f"image-{uid}"`` so at most one task touches
        a given image at a time.
        """
        try:
            for uid in image_uids:
                await post_process_image.configure(
                    lock=f"image-{uid}",
                ).defer_async(image_uid=str(uid))
        except Exception:
            self._logger.error("Error deferring post-process tasks", exc_info=True)

    async def post_process_image(self, image: Image):
        """Defer post-processing for one image.

        Same per-image ``lock`` as :meth:`post_process_images`.
        """
        self._logger.info(f"Post processing image {image.uid}")
        try:
            await post_process_image.configure(
                lock=f"image-{image.uid}",
            ).defer_async(image_uid=str(image.uid))
        except Exception:
            self._logger.error(
                f"Error post-processing image {image.uid}", exc_info=True
            )

    async def metadata_project_export(self, project: Project):
        """Defer metadata export for a project.

        ``lock=f"export-{project_uid}"`` serialises export per project.
        """
        self._logger.info(f"Exporting metadata for project {project.uid}")
        try:
            await process_metadata_export.configure(
                lock=f"export-{project.uid}",
            ).defer_async(project_id=str(project.uid))
        except Exception:
            self._logger.error(
                f"Error exporting metadata for project {project.uid}", exc_info=True
            )

    async def store_images_in_batch(self, batch: Batch):
        """Defer outbox-move for a batch.

        ``lock=f"store-{batch_uid}"`` serialises the outbox move per batch.
        """
        self._logger.info(f"Storing images for batch {batch.uid}")
        try:
            await store_batch_images_to_outbox.configure(
                lock=f"store-{batch.uid}",
            ).defer_async(batch_uid=str(batch.uid))
        except Exception:
            self._logger.error(
                f"Error storing images for batch {batch.uid}", exc_info=True
            )

    async def metadata_batch_import(self, batch: Batch, search_parameters: Any):
        """Defer a metadata search for the given batch.

        ``lock=f"metadata-import-{project_uid}"`` — at most one metadata
        search runs per project at a time; different projects search
        concurrently subject to worker slot availability.

        ``queueing_lock=f"metadata-import-batch-{batch_uid}"`` — enqueue
        dedup: re-triggering the same batch's search while a previous one
        is queued or in-flight raises :exc:`AlreadyEnqueued`, which we log
        and swallow for idempotent "search started" semantics.
        """
        self._logger.info(f"Importing metadata for batch {batch.uid}: {batch.name}")
        try:
            await process_metadata_import.configure(
                lock=f"metadata-import-{batch.project_uid}",
                queueing_lock=f"metadata-import-batch-{batch.uid}",
            ).defer_async(
                batch_uid=str(batch.uid),
                search_parameters=search_parameters,
            )
        except AlreadyEnqueued:
            self._logger.info(
                f"Metadata search for batch {batch.uid} is already queued or "
                f"running; ignoring duplicate trigger."
            )
        except Exception:
            self._logger.error(
                f"Error importing metadata for batch {batch.uid}: {batch.name}",
                exc_info=True,
            )

    async def metadata_retry_search_item(self, search_item_uid: UUID):
        self._logger.info(f"Retrying metadata search item {search_item_uid}")
        try:
            await retry_metadata_search_item.defer_async(
                search_item_uid=str(search_item_uid)
            )
        except Exception:
            self._logger.error(
                f"Error scheduling retry for search item {search_item_uid}",
                exc_info=True,
            )

    async def remap_batch_attributes(self, batch_uid: UUID):
        """Defer mapper re-application for a batch.

        ``lock=f"remap-batch-{batch_uid}"`` serialises per batch.
        """
        self._logger.info(f"Remapping attributes in batch {batch_uid}")
        try:
            await remap_batch_attributes.configure(
                lock=f"remap-batch-{batch_uid}",
            ).defer_async(batch_uid=str(batch_uid))
        except Exception:
            self._logger.error(
                f"Error scheduling remap for batch {batch_uid}", exc_info=True
            )

    async def remap_dataset_attributes(self, dataset_uid: UUID):
        """Defer mapper re-application for a dataset.

        ``lock=f"remap-dataset-{dataset_uid}"`` serialises per dataset.
        """
        self._logger.info(f"Remapping attributes in dataset {dataset_uid}")
        try:
            await remap_dataset_attributes.configure(
                lock=f"remap-dataset-{dataset_uid}",
            ).defer_async(dataset_uid=str(dataset_uid))
        except Exception:
            self._logger.error(
                f"Error scheduling remap for dataset {dataset_uid}", exc_info=True
            )
