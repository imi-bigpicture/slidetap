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

"""Background task definitions.

Each ``@dishka_task`` declaration registers a Procrastinate task and
its Dishka-resolved dependencies. Tasks are routed across three queues
(``image_processing``, ``metadata_import``, ``default``) so workers can
be sized per workload. A per-task ``priority`` controls dispatch order
within a queue when slots free.

Image tasks (``download_and_pre_process_image``, ``post_process_image``)
are idempotent under redelivery: an entry guard inspects the image's
status to decide whether to run both phases, only pre-process, take
over from a dead worker, or skip. ``inject_task_id=True`` makes the
current job id available as a ``task_id`` parameter for the entry guard
to record on the image row.
"""

import logging
from collections.abc import Callable
from enum import IntEnum, StrEnum
from typing import Any
from uuid import UUID

from dishka import FromDishka
from procrastinate import App as TaskApp
from procrastinate import Blueprint, RetryStrategy
from procrastinate.jobs import Job as TaskJob

from slidetap.config import TaskConfig
from slidetap.database import (
    DatabaseImage,
    DatabaseImageFile,
    DatabaseMetadataSearchItem,
)
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
    TransientTaskError,
)
from slidetap.model import ImageStatus
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    ItemService,
    MapperService,
    MetadataSearchItemService,
    ProjectService,
    SchemaService,
    StorageService,
)
from slidetap.task.dishka_integration import dishka_task

logger = logging.getLogger(__name__)


slidetap_tasks = Blueprint()
"""Procrastinate blueprint that every task in this module registers against.

The :class:`App` constructed via :class:`TaskAppProvider` attaches this
blueprint at construction time.
"""


class TaskQueue(StrEnum):
    """Routing labels for task definitions."""

    IMAGE = "image_processing"
    METADATA = "metadata_import"
    DEFAULT = "default"


class TaskPriority(IntEnum):
    """Dispatch priority — higher value picked first when a slot frees."""

    LOW = -10
    """Long-running work — image processing, bulk metadata import."""

    NORMAL = 0
    """Default-importance work."""

    HIGH = 10
    """Quick, latency-sensitive tasks — retries, remaps."""


_TRANSIENT_RETRY = RetryStrategy(
    max_attempts=3,
    exponential_wait=3,
    retry_exceptions=[TransientTaskError],
)
"""Retry policy for tasks that may hit transient failures.

Implementations of the external interfaces signal "retry me" by raising
:class:`TransientTaskError`. Any other exception is terminal and ends the
task in its failure path (status FAILED, FAILED batch, etc.). Waits
scale exponentially: 3 s, 9 s, 27 s — total ~40 s across three attempts.
"""


def _record_image_phase_failure(
    database_image: DatabaseImage,
    exception: BaseException,
    failed_setter: Callable[[], None],
    fallback_status: ImageStatus,
) -> None:
    try:
        database_image.set_status_message(str(exception))
        failed_setter()
    except Exception:
        logger.error(
            f"Also failed to set failure status for {database_image.uid}, "
            f"force-setting",
            exc_info=True,
        )
        database_image.status = fallback_status
        database_image.set_status_message(str(exception))


@dishka_task(
    slidetap_tasks,
    name="download_and_pre_process_image",
    queue=TaskQueue.IMAGE,
    priority=TaskPriority.LOW,
    inject_task_id=True,
    retry=_TRANSIENT_RETRY,
)
def download_and_pre_process_image(
    image_uid: UUID | str,
    task_id: str,
    image_import_interface: FromDishka[ImageImportInterface],
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    item_service: FromDishka[ItemService],
    batch_service: FromDishka[BatchService],
    attribute_service: FromDishka[AttributeService],
) -> None:
    """Download then pre-process the image with given UID.

    Idempotent under redelivery. The entry guard checks status and bails
    on work already in progress; jobs left in-progress by a dead worker
    are recovered by the periodic :func:`retry_stalled_jobs` task, which
    resets status before re-queueing.
    """
    if isinstance(image_uid, str):
        image_uid = UUID(image_uid)
    logger.info(f"Download and pre-process image {image_uid}")

    with database_service.get_session() as session:
        database_image = database_service.get_image_for_update(session, image_uid)

        if (
            database_image.pre_processed
            or database_image.post_processing
            or database_image.post_processing_failed
            or database_image.processed
            or database_image.storing_failed
        ):
            logger.info(
                f"Image {image_uid} already past pre-processing "
                f"(status={database_image.status.name}), skipping"
            )
            return

        if database_image.downloading or database_image.pre_processing:
            logger.info(
                f"Image {image_uid} already in progress "
                f"(status={database_image.status.name}), skipping"
            )
            return

        if database_image.not_started:
            database_image.set_as_downloading()
            session.commit()
            needs_download = True
        elif database_image.downloaded:
            database_image.set_as_pre_processing()
            session.commit()
            needs_download = False
        else:
            logger.info(
                f"Image {image_uid} in non-resumable state "
                f"(status={database_image.status.name}), skipping"
            )
            return

    if needs_download:
        downloaded = _run_download_phase(
            image_uid,
            image_import_interface,
            database_service,
            item_service,
        )
        if not downloaded:
            return

        with database_service.get_session() as session:
            database_image = database_service.get_image_for_update(session, image_uid)
            if not database_image.downloaded:
                logger.warning(
                    f"Image {image_uid} not in DOWNLOADED after download "
                    f"(status={database_image.status.name}), skipping pre-process"
                )
                return
            database_image.set_as_pre_processing()
            session.commit()

    pre_processed = _run_pre_process_phase(
        image_uid,
        task_id,
        metadata_import_interface,
        database_service,
        attribute_service,
    )
    if not pre_processed:
        return

    with database_service.get_session() as session:
        database_image = database_service.get_image(session, image_uid)
        if database_image.batch is None:
            return
        any_non_completed = database_service.get_first_image_for_batch(
            session,
            batch_uid=database_image.batch.uid,
            exclude_status=[
                ImageStatus.PRE_PROCESSING_FAILED,
                ImageStatus.PRE_PROCESSED,
            ],
            selected=True,
        )
        if any_non_completed is not None:
            logger.debug(
                f"Batch {database_image.batch.uid} not yet finished pre-processing. "
                f"Image {any_non_completed.uid} has status {any_non_completed.status}."
            )
            return
        logger.debug(f"Batch {database_image.batch.uid} pre-processed.")
        batch_service.set_as_pre_processed(database_image.batch, session=session)


def _run_download_phase(
    image_uid: UUID,
    image_import_interface: ImageImportInterface,
    database_service: DatabaseService,
    item_service: ItemService,
) -> bool:
    try:
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            if database_image.batch is None:
                raise AssertionError("Image batch is None")
            image_folder, image_files = image_import_interface.download(
                database_image.model, database_image.batch.project.model
            )
            database_image.files.clear()
            database_image.folder_path = str(image_folder)
            for image_file in image_files:
                database_image_file = DatabaseImageFile(database_image, image_file.name)
                session.add(database_image_file)
                database_image.files.add(database_image_file)
            database_image.set_as_downloaded()
        return True
    except TransientTaskError:
        # Reset state so the retry's entry guard can re-claim the row.
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            database_image.reset_as_not_started()
        raise
    except Exception as exception:
        logger.error(f"Failed to download image {image_uid}", exc_info=True)
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            _record_image_phase_failure(
                database_image,
                exception,
                database_image.set_as_downloading_failed,
                ImageStatus.DOWNLOADING_FAILED,
            )
            item_service.select_item(database_image, False, session=session)
        return False


def _run_pre_process_phase(
    image_uid: UUID,
    task_id: str,
    metadata_import_interface: MetadataImportInterface,
    database_service: DatabaseService,
    attribute_service: AttributeService,
) -> bool:
    try:
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            if database_image.batch is None:
                raise AssertionError("Image batch is None")
            image = metadata_import_interface.import_image_metadata(
                database_image.model,
                database_image.batch.model,
                database_image.batch.project.model,
                task_id,
            )
            database_image.folder_path = str(image.folder_path)
            database_image.files.clear()
            for image_file in image.files:
                new_file = DatabaseImageFile(database_image, image_file.filename)
                session.add(new_file)
                database_image.files.add(new_file)
            attribute_service.update_for_item(
                database_image, image.attributes.values(), session
            )
            database_image.set_as_pre_processed()
        return True
    except TransientTaskError:
        # Reset state so the retry's entry guard can re-claim the row.
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            database_image.reset_as_downloaded()
        raise
    except Exception as exception:
        logger.error(f"Failed to pre-process image {image_uid}", exc_info=True)
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            _record_image_phase_failure(
                database_image,
                exception,
                database_image.set_as_pre_processing_failed,
                ImageStatus.PRE_PROCESSING_FAILED,
            )
        return False


@dishka_task(
    slidetap_tasks,
    name="post_process_image",
    queue=TaskQueue.IMAGE,
    priority=TaskPriority.LOW,
    inject_task_id=True,
    retry=_TRANSIENT_RETRY,
)
def post_process_image(
    image_uid: UUID | str,
    task_id: str,
    image_export_interface: FromDishka[ImageExportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    storage_service: FromDishka[StorageService],
) -> None:
    if isinstance(image_uid, str):
        image_uid = UUID(image_uid)
    logger.info(f"Post processing image {image_uid}")

    with database_service.get_session() as session:
        database_image = database_service.get_image_for_update(session, image_uid)
        if not database_image.pre_processed:
            logger.info(
                f"Image {image_uid} not in PRE_PROCESSED state "
                f"(status={database_image.status.name}), skipping"
            )
            session.commit()
            return
        database_image.set_as_post_processing()
        session.commit()

    project = None
    with database_service.get_session() as session:
        database_image = database_service.get_image(session, image_uid)

        try:
            if database_image.batch is None:
                raise AssertionError("Image batch is None")
            project = database_image.batch.project.model
            image = image_export_interface.export(
                database_image.model,
                database_image.batch.model,
                project,
                task_id=task_id,
            )

            database_image.folder_path = str(image.folder_path)
            database_image.thumbnail_path = (
                str(image.thumbnail_path) if image.thumbnail_path else None
            )
            database_image.files.clear()
            for image_file in image.files:
                new_file = DatabaseImageFile(database_image, image_file.filename)
                session.add(new_file)
                database_image.files.add(new_file)
            database_image.format = image.format
            database_image.set_as_post_processed()
        except TransientTaskError:
            session.rollback()
            if project is not None:
                storage_service.cleanup_processing_task(project, task_id)
            # Reset state so the retry's entry guard re-claims the row.
            database_image.reset_as_pre_processed()
            session.commit()
            raise
        except Exception as exception:
            session.rollback()
            logger.error(f"Failed to post-process image {image_uid}", exc_info=True)
            if project is not None:
                storage_service.cleanup_processing_task(project, task_id)
            _record_image_phase_failure(
                database_image,
                exception,
                database_image.set_as_post_processing_failed,
                ImageStatus.POST_PROCESSING_FAILED,
            )

        if database_image.batch is None:
            return
        session.commit()
        any_non_completed = database_service.get_first_image_for_batch(
            session,
            batch_uid=database_image.batch.uid,
            exclude_status=[
                ImageStatus.POST_PROCESSING_FAILED,
                ImageStatus.POST_PROCESSED,
            ],
            selected=True,
        )
        if any_non_completed is not None:
            logger.debug(
                f"Batch {database_image.batch.uid} not yet finished post-processing. "
                f"Image {any_non_completed.uid} has status {any_non_completed.status}."
            )
            return
        logger.debug(f"Batch {database_image.batch.uid} post-processed.")
        batch_service.set_as_post_processed(database_image.batch, session=session)


@dishka_task(
    slidetap_tasks,
    name="store_batch_images_to_outbox",
    queue=TaskQueue.IMAGE,
    priority=TaskPriority.LOW,
    retry=_TRANSIENT_RETRY,
)
def store_batch_images_to_outbox(
    batch_uid: UUID | str,
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    storage_service: FromDishka[StorageService],
    schema_service: FromDishka[SchemaService],
) -> None:
    """Move post-processed images from the processing directory to the outbox.

    Each image is stored and set as stored one image at a time, so that a failure
    part-way through the batch cannot leave images on record in the processing
    directory they have already been moved out of, and so that a retry, which
    only selects images that are post-processed, resumes where the failed attempt
    left off.

    An image that cannot be stored is set as storing failed, and the batch is not
    completed: the dataset in the outbox is missing an image, and the batch stays
    storing until the image has been retried and stored. An image left as storing
    by a failed attempt is stored again, as storing an already stored image is a
    no-op.
    """
    if isinstance(batch_uid, str):
        batch_uid = UUID(batch_uid)
    logger.info(f"Storing batch {batch_uid} images to outbox")

    with database_service.get_session(commit=False) as session:
        database_batch = database_service.get_batch(session, batch_uid)
        project = database_batch.project.model
        dataset = database_service.get_dataset(session, project.dataset_uid).model

        image_models = []
        for image_schema in schema_service.images.values():
            for database_image in database_service.get_images(
                session,
                schema=image_schema,
                batch=batch_uid,
                selected=True,
                status_filter=[ImageStatus.POST_PROCESSED, ImageStatus.STORING],
            ):
                image_models.append(database_image.model)

    for image_model in image_models:
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_model.uid)
            database_image.set_as_storing()
        try:
            storage_service.store_image_to_outbox(project, image_model, dataset)
        except TransientTaskError:
            raise
        except Exception as exception:
            logger.error(f"Failed to store image {image_model.uid}", exc_info=True)
            with database_service.get_session() as session:
                database_image = database_service.get_image(session, image_model.uid)
                _record_image_phase_failure(
                    database_image,
                    exception,
                    database_image.set_as_storing_failed,
                    ImageStatus.STORING_FAILED,
                )
            continue
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_model.uid)
            database_image.folder_path = image_model.folder_path
            database_image.thumbnail_path = image_model.thumbnail_path
            database_image.set_as_stored()

    with database_service.get_session() as session:
        database_batch = database_service.get_batch(session, batch_uid)
        failed_image = batch_service.image_that_failed_to_store(database_batch, session)
        if failed_image is not None:
            # The dataset in the outbox is missing an image, and the batch is thus
            # not complete. It stays storing, to be stored again once the image
            # that failed has been retried, or excluded from the batch.
            logger.warning(
                f"Batch {batch_uid} not completed, image {failed_image.uid} failed "
                f"to store. Retry the image to store it, or deselect it to complete "
                f"the batch without it."
            )
            return
        batch_service.set_as_completed(database_batch, session=session)


@dishka_task(
    slidetap_tasks,
    name="remap_batch_attributes",
    queue=TaskQueue.DEFAULT,
    priority=TaskPriority.HIGH,
    retry=_TRANSIENT_RETRY,
)
def remap_batch_attributes(
    batch_uid: UUID | str,
    mapper_service: FromDishka[MapperService],
) -> None:
    """Re-apply the project's mappers to every attribute in a batch.

    Idempotent: re-running yields the same result as long as the mapping
    rules are unchanged, so redelivery is safe.
    """
    if isinstance(batch_uid, str):
        batch_uid = UUID(batch_uid)
    logger.info(f"Remapping attributes in batch {batch_uid}")
    mapper_service.remap_batch(batch_uid)


@dishka_task(
    slidetap_tasks,
    name="remap_dataset_attributes",
    queue=TaskQueue.DEFAULT,
    priority=TaskPriority.HIGH,
    retry=_TRANSIENT_RETRY,
)
def remap_dataset_attributes(
    dataset_uid: UUID | str,
    mapper_service: FromDishka[MapperService],
) -> None:
    """Re-apply the project's mappers to every attribute in a dataset."""
    if isinstance(dataset_uid, str):
        dataset_uid = UUID(dataset_uid)
    logger.info(f"Remapping attributes in dataset {dataset_uid}")
    mapper_service.remap_dataset(dataset_uid)


@dishka_task(
    slidetap_tasks,
    name="process_metadata_export",
    queue=TaskQueue.DEFAULT,
    priority=TaskPriority.NORMAL,
    retry=_TRANSIENT_RETRY,
)
def process_metadata_export(
    project_id: UUID | str,
    metadata_export_interface: FromDishka[MetadataExportInterface],
    project_service: FromDishka[ProjectService],
    database_service: FromDishka[DatabaseService],
) -> None:
    if isinstance(project_id, str):
        project_id = UUID(project_id)
    logger.info(f"Exporting metadata for project {project_id}")
    with database_service.get_session() as session:
        database_project = database_service.get_project(session, project_id)
        if not database_project.exporting:
            return
        try:
            metadata_export_interface.export(
                database_project.model, database_project.dataset.model
            )
            project_service.set_as_export_complete(database_project, session)
        except TransientTaskError:
            raise
        except Exception:
            logger.error(
                f"Failed to export metadata for project {project_id}", exc_info=True
            )
            project_service.revert_export(database_project, session)


@dishka_task(
    slidetap_tasks,
    name="process_metadata_import",
    queue=TaskQueue.METADATA,
    priority=TaskPriority.LOW,
    retry=_TRANSIENT_RETRY,
)
def process_metadata_import(
    batch_uid: UUID | str,
    search_parameters: Any,
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    item_service: FromDishka[ItemService],
    search_item_service: FromDishka[MetadataSearchItemService],
) -> None:
    """Drive the metadata search for a batch.

    For each ``MetadataSearchResult`` yielded by the importer, create one
    search-item row. Failures are recorded as FAILED with no items
    persisted; successful units have their items persisted in dependency
    order with a per-unit commit (rollback isolated to that unit on
    persist error).
    """
    if isinstance(batch_uid, str):
        batch_uid = UUID(batch_uid)
    logger.info(f"Importing metadata for batch {batch_uid}")
    with database_service.get_session() as session:
        database_batch = database_service.get_batch(session, batch_uid)
        if not database_batch.metadata_searching:
            return
        batch = database_batch.model
        dataset = database_batch.project.dataset.model
        mappers = [
            mapper.model
            for group in database_batch.project.mapper_groups
            for mapper in group.mappers
        ]

    try:
        results = metadata_import_interface.search(batch, dataset, search_parameters)
        for result in results:
            with database_service.get_session() as session:
                search_item = search_item_service.create(
                    batch_uid=batch_uid,
                    identifier=result.identifier,
                    schema_uid=result.schema_uid,
                    session=session,
                )
                if result.is_failure:
                    search_item_service.mark_failed(
                        search_item,
                        result.failure_message or "Import failed",
                        session=session,
                    )
                    session.commit()
                    continue

                existing = None
                if result.item_uid is not None:
                    existing = database_service.get_optional_item(
                        session, result.item_uid
                    )
                if existing is None:
                    existing = database_service.get_optional_item_by_identifier(
                        session,
                        result.identifier,
                        result.schema_uid,
                        dataset.uid,
                    )
                if existing is not None:
                    search_item_service.mark_complete(
                        search_item, existing.uid, session=session
                    )
                    logger.info(
                        f"Skipping search result {result.identifier}: item "
                        f"already in dataset (uid {existing.uid})."
                    )
                    session.commit()
                    continue

                try:
                    with session.begin_nested():
                        result_item_uid = item_service.add_search_result(
                            result, mappers, session=session
                        )
                        search_item_service.mark_complete(
                            search_item, result_item_uid, session=session
                        )
                except TransientTaskError:
                    raise
                except Exception as exception:
                    logger.error(
                        f"Failed to persist search result {result.identifier} "
                        f"in batch {batch_uid}",
                        exc_info=True,
                    )
                    search_item_service.mark_failed(
                        search_item, str(exception), session=session
                    )
                session.commit()
        with database_service.get_session() as session:
            database_batch = database_service.get_batch(session, batch_uid)
            batch_service.set_as_search_complete(database_batch, session)
    except TransientTaskError:
        raise
    except Exception:
        logger.error(f"Failed to import metadata for batch {batch_uid}", exc_info=True)
        with database_service.get_session() as session:
            database_batch = database_service.get_batch(session, batch_uid)
            batch_service.set_as_failed(database_batch, session)


@dishka_task(
    slidetap_tasks,
    name="retry_metadata_search_item",
    queue=TaskQueue.METADATA,
    priority=TaskPriority.HIGH,
    retry=_TRANSIENT_RETRY,
)
def retry_metadata_search_item(
    search_item_uid: UUID | str,
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    item_service: FromDishka[ItemService],
    search_item_service: FromDishka[MetadataSearchItemService],
) -> None:
    """Re-run metadata import for a single previously-failed search item."""
    if isinstance(search_item_uid, str):
        search_item_uid = UUID(search_item_uid)
    logger.info(f"Retrying metadata search item {search_item_uid}")
    with database_service.get_session() as session:
        database_search_item = session.get(DatabaseMetadataSearchItem, search_item_uid)
        if database_search_item is None:
            logger.warning(f"Search item {search_item_uid} not found for retry")
            return
        database_batch = database_service.get_batch(
            session, database_search_item.batch_uid
        )
        search_item = database_search_item.model
        batch = database_batch.model
        dataset = database_batch.project.dataset.model
        mappers = [
            mapper.model
            for group in database_batch.project.mapper_groups
            for mapper in group.mappers
        ]

    try:
        result = metadata_import_interface.retry_item(search_item, batch, dataset)
    except TransientTaskError:
        raise
    except Exception as exception:
        logger.error(
            f"Hard failure retrying search item {search_item_uid}", exc_info=True
        )
        with database_service.get_session() as session:
            search_item_service.mark_failed(
                search_item_uid, str(exception), session=session
            )
            session.commit()
        return

    with database_service.get_session() as session:
        if result.is_failure:
            search_item_service.mark_failed(
                search_item_uid,
                result.failure_message or "Import failed",
                session=session,
            )
        else:
            try:
                with session.begin_nested():
                    item_uid = item_service.add_search_result(
                        result, mappers, session=session
                    )
                    search_item_service.mark_complete(
                        search_item_uid, item_uid, session=session
                    )
            except TransientTaskError:
                raise
            except Exception as exception:
                logger.error(
                    f"Failed to persist retry result for search item {search_item_uid}",
                    exc_info=True,
                )
                search_item_service.mark_failed(
                    search_item_uid, str(exception), session=session
                )
        session.commit()


_RECOVERY_CRON = "*/5 * * * *"
"""Run periodic self-healing every 5 minutes."""


_STALLED_RECOVERY_MARGIN = 4


_RECOVERY_LOCK = "retry_stalled_jobs"
"""Shared ``lock`` and ``queueing_lock`` for the recovery task.

``queueing_lock`` allows at most one run waiting in ``todo``; ``lock`` allows at
most one run in ``doing``. Together they keep back-filled or overlapping ticks
from executing in parallel, so two recovery runs can't race each other on
``retry_job``.
"""


@slidetap_tasks.periodic(cron=_RECOVERY_CRON)
@dishka_task(
    slidetap_tasks,
    name="retry_stalled_jobs",
    queue=TaskQueue.DEFAULT,
    priority=TaskPriority.HIGH,
    lock=_RECOVERY_LOCK,
    queueing_lock=_RECOVERY_LOCK,
)
async def retry_stalled_jobs(
    timestamp: int,
    database_service: FromDishka[DatabaseService],
    config: FromDishka[TaskConfig],
    app: FromDishka[TaskApp],
) -> None:
    """Re-queue jobs whose worker has gone silent.

    Uses Procrastinate's worker heartbeat: any job in ``doing`` whose
    worker hasn't beat for ``_STALLED_RECOVERY_MARGIN ×
    stalled_worker_timeout`` is treated as abandoned. Image
    tasks need their domain status reset first because their entry
    guards bail on in-progress status.
    """
    threshold = _STALLED_RECOVERY_MARGIN * config.stalled_worker_timeout
    stalled = list(
        await app.job_manager.get_stalled_jobs(seconds_since_heartbeat=threshold)
    )
    if not stalled:
        return
    logger.warning(f"Recovering {len(stalled)} stalled job(s).")
    for job in stalled:
        _reset_state_for_stalled_job(database_service, job)
        await app.job_manager.retry_job(job)


def _reset_state_for_stalled_job(
    database_service: DatabaseService, job: TaskJob
) -> None:
    """Reset domain status so the retried job's entry guard doesn't bail."""
    short_name = (job.task_name or "").rsplit(":", 1)[-1]
    kwargs = job.task_kwargs or {}

    if short_name in ("download_and_pre_process_image", "post_process_image"):
        image_uid_str = kwargs.get("image_uid")
        if not isinstance(image_uid_str, str):
            return
        with database_service.get_session() as session:
            image = database_service.get_image(session, UUID(image_uid_str))
            if image is None:
                return
            if image.status == ImageStatus.DOWNLOADING:
                image.reset_as_not_started()
            elif image.status == ImageStatus.PRE_PROCESSING:
                image.reset_as_downloaded()
            elif image.status == ImageStatus.POST_PROCESSING:
                image.reset_as_pre_processed()
