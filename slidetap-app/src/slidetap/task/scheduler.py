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
from collections.abc import Iterable, Mapping
from typing import Any
from uuid import UUID

from procrastinate import App as TaskApp
from procrastinate.exceptions import AlreadyEnqueued

from slidetap.model import Batch, Image, Project
from slidetap.task.tasks import (
    complete_schema_migration,
    delete_batch,
    delete_project,
    download_and_pre_process_image,
    plan_schema_migration,
    post_process_image,
    process_metadata_export,
    process_metadata_import,
    remap_batch_attributes,
    remap_dataset_attributes,
    retry_metadata_search_item,
    store_batch_images_to_outbox,
)


class DeferError(Exception):
    """Tasks for some of the images could not be deferred.

    Raised once every image has been tried, so that one image failing to be
    deferred does not keep the others from being processed.
    """

    def __init__(self, failures: Mapping[UUID, BaseException]):
        self.failures = dict(failures)
        first = next(iter(self.failures.values()), None)
        super().__init__(
            f"Failed to defer tasks for {len(self.failures)} image(s): {first}"
        )


class Scheduler:
    """Interface for starting background tasks.

    The Procrastinate :class:`App` is expected to be opened synchronously for
    the process lifetime (see :class:`SlideTapWebAppFactory`'s lifespan), so
    methods only call ``...defer(...)``; they do not open or close the
    connector themselves. Deferring is synchronous, through the connector's
    sync pool, so it can be called from any thread of the web app.

    A task that cannot be deferred raises, so that the caller, which has
    usually already set what the task works on as waiting for it, can set it
    as failed rather than leave it waiting for a job that does not exist.
    """

    def __init__(self, app: TaskApp):
        self._app = app
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def pre_process_images(self, image_uids: Iterable[UUID]) -> None:
        """Defer pre-processing for each image.

        Each task takes ``lock=f"image-{uid}"`` so at most one task touches
        a given image at a time. Per-image entry guards still apply; the
        lock is an upstream filter that keeps the worker from picking up
        a job whose guard would just bail.

        Raises
        ------
        DeferError
            Naming the images whose task could not be deferred, once every
            image has been tried.
        """
        self._defer_each(download_and_pre_process_image, image_uids)

    def download_and_pre_process_image(self, image: Image):
        """Defer pre-processing for one image.

        Same per-image ``lock`` as :meth:`pre_process_images`. Raises if the
        task cannot be deferred.
        """
        self._logger.info(f"Downloading and pre-processing image {image.uid}")
        download_and_pre_process_image.configure(
            lock=f"image-{image.uid}",
        ).defer(image_uid=str(image.uid))

    def post_process_images(self, image_uids: Iterable[UUID]) -> None:
        """Defer post-processing for each image.

        Each task takes ``lock=f"image-{uid}"`` so at most one task touches
        a given image at a time.

        Raises
        ------
        DeferError
            Naming the images whose task could not be deferred, once every
            image has been tried.
        """
        self._defer_each(post_process_image, image_uids)

    def post_process_image(self, image: Image):
        """Defer post-processing for one image.

        Same per-image ``lock`` as :meth:`post_process_images`. Raises if the
        task cannot be deferred.
        """
        self._logger.info(f"Post processing image {image.uid}")
        post_process_image.configure(
            lock=f"image-{image.uid}",
        ).defer(image_uid=str(image.uid))

    def _defer_each(self, task: Any, image_uids: Iterable[UUID]) -> None:
        """Defer the image task for each image, trying every one of them."""
        failures: dict[UUID, BaseException] = {}
        for image_uid in image_uids:
            try:
                task.configure(lock=f"image-{image_uid}").defer(
                    image_uid=str(image_uid)
                )
            except Exception as exception:
                self._logger.error(
                    f"Error deferring {task.name} for image {image_uid}",
                    exc_info=True,
                )
                failures[image_uid] = exception
        if failures:
            raise DeferError(failures)

    def metadata_project_export(self, project: Project):
        """Defer metadata export for a project.

        ``lock=f"export-{project_uid}"`` serialises export per project.
        Raises if the task cannot be deferred.
        """
        self._logger.info(f"Exporting metadata for project {project.uid}")
        process_metadata_export.configure(
            lock=f"export-{project.uid}",
        ).defer(project_id=str(project.uid))

    def plan_migration(self, project_uid: UUID) -> None:
        """Defer planning the migration of a project to another root schema.

        ``lock=f"migrate-{project_uid}"`` serialises the steps of a migration.
        Raises if the task cannot be deferred.
        """
        self._logger.info(f"Planning the migration of project {project_uid}")
        plan_schema_migration.configure(
            lock=f"migrate-{project_uid}",
        ).defer(project_uid=str(project_uid))

    def complete_migration(self, project_uid: UUID) -> None:
        """Defer completing the migration of a project, as `plan_migration`."""
        self._logger.info(f"Completing the migration of project {project_uid}")
        complete_schema_migration.configure(
            lock=f"migrate-{project_uid}",
        ).defer(project_uid=str(project_uid))

    def store_images_in_batch(self, batch: Batch):
        """Defer outbox-move for a batch.

        ``lock=f"store-{batch_uid}"`` serialises the outbox move per batch.
        Raises if the task cannot be deferred.
        """
        self._logger.info(f"Storing images for batch {batch.uid}")
        store_batch_images_to_outbox.configure(
            lock=f"store-{batch.uid}",
        ).defer(batch_uid=str(batch.uid))

    def metadata_batch_import(self, batch: Batch, search_parameters: Any):
        """Defer a metadata search for the given batch.

        ``lock=f"metadata-import-{project_uid}"`` — at most one metadata
        search runs per project at a time; different projects search
        concurrently subject to worker slot availability.

        ``queueing_lock=f"metadata-import-batch-{batch_uid}"`` — enqueue
        dedup: re-triggering the same batch's search while a previous one
        is queued or in-flight raises :exc:`AlreadyEnqueued`, which we log
        and swallow for idempotent "search started" semantics.

        Any other deferral failure is raised to the caller, which has already
        set the batch as searching and must undo that.
        """
        self._logger.info(f"Importing metadata for batch {batch.uid}: {batch.name}")
        try:
            process_metadata_import.configure(
                lock=f"metadata-import-{batch.project_uid}",
                queueing_lock=f"metadata-import-batch-{batch.uid}",
            ).defer(
                batch_uid=str(batch.uid),
                search_parameters=search_parameters,
            )
        except AlreadyEnqueued:
            self._logger.info(
                f"Metadata search for batch {batch.uid} is already queued or "
                f"running; ignoring duplicate trigger."
            )

    def metadata_retry_search_item(self, search_item_uid: UUID):
        """Defer the retry of a search item. Raises if it cannot be deferred."""
        self._logger.info(f"Retrying metadata search item {search_item_uid}")
        retry_metadata_search_item.defer(search_item_uid=str(search_item_uid))

    def remap_batch_attributes(self, batch_uid: UUID):
        """Defer mapper re-application for a batch.

        ``lock=f"remap-batch-{batch_uid}"`` serialises per batch. Raises if the
        task cannot be deferred.
        """
        self._logger.info(f"Remapping attributes in batch {batch_uid}")
        remap_batch_attributes.configure(
            lock=f"remap-batch-{batch_uid}",
        ).defer(batch_uid=str(batch_uid))

    def delete_batch(self, batch: Batch) -> None:
        """Defer the deletion of a batch marked as deleting.

        ``lock=f"delete-project-{project_uid}"`` serialises deletes within a
        project, whether of a batch or of the project itself.

        ``queueing_lock=f"delete-batch-{batch_uid}"`` dedupes: marking the
        batch again while its delete is queued raises :exc:`AlreadyEnqueued`,
        which is logged and swallowed, since the delete is on its way either
        way. Any other deferral failure is raised to the caller: the batch
        stays marked, and marking it again defers it again.
        """
        self._logger.info(f"Deleting batch {batch.uid}")
        try:
            delete_batch.configure(
                lock=f"delete-project-{batch.project_uid}",
                queueing_lock=f"delete-batch-{batch.uid}",
            ).defer(batch_uid=str(batch.uid))
        except AlreadyEnqueued:
            self._logger.info(
                f"Deletion of batch {batch.uid} is already queued; ignoring "
                "duplicate trigger."
            )

    def delete_project(self, project: Project) -> None:
        """Defer the deletion of a project marked as deleting.

        Same lock as :meth:`delete_batch`, and a
        ``queueing_lock=f"delete-project-{project_uid}"`` that dedupes the
        same way.
        """
        self._logger.info(f"Deleting project {project.uid}")
        try:
            delete_project.configure(
                lock=f"delete-project-{project.uid}",
                queueing_lock=f"delete-project-{project.uid}",
            ).defer(project_uid=str(project.uid))
        except AlreadyEnqueued:
            self._logger.info(
                f"Deletion of project {project.uid} is already queued; ignoring "
                "duplicate trigger."
            )

    def remap_dataset_attributes(self, dataset_uid: UUID):
        """Defer mapper re-application for a dataset.

        ``lock=f"remap-dataset-{dataset_uid}"`` serialises per dataset. Raises if
        the task cannot be deferred.
        """
        self._logger.info(f"Remapping attributes in dataset {dataset_uid}")
        remap_dataset_attributes.configure(
            lock=f"remap-dataset-{dataset_uid}",
        ).defer(dataset_uid=str(dataset_uid))
