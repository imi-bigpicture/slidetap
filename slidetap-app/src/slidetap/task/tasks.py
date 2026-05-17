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
from datetime import datetime, timedelta, timezone
from enum import IntEnum, StrEnum
from typing import Any, Callable, Union
from uuid import UUID

from dishka import FromDishka
from procrastinate import App as TaskApp
from procrastinate import Blueprint
from sqlalchemy import select

from slidetap.config import SlideTapConfig
from slidetap.database import (
    DatabaseBatch,
    DatabaseImage,
    DatabaseImageFile,
    DatabaseMetadataSearchItem,
)
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.model import BatchStatus, ImageStatus
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
from slidetap.task.heartbeat import ImageHeartbeat

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


def _record_image_phase_failure(
    database_image: DatabaseImage,
    exception: BaseException,
    failed_setter: Callable[[], None],
    fallback_status: ImageStatus,
) -> None:
    try:
        database_image.status_message = str(exception)
        failed_setter()
    except Exception:
        logger.error(
            f"Also failed to set failure status for {database_image.uid}, "
            f"force-setting",
            exc_info=True,
        )
        database_image.status = fallback_status
        database_image.status_message = str(exception)
        database_image.last_heartbeat_at = None


@dishka_task(
    slidetap_tasks,
    name="download_and_pre_process_image",
    queue=TaskQueue.IMAGE,
    priority=TaskPriority.LOW,
    inject_task_id=True,
)
def download_and_pre_process_image(
    image_uid: Union[UUID, str],
    task_id: str,
    image_import_interface: FromDishka[ImageImportInterface],
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    item_service: FromDishka[ItemService],
    batch_service: FromDishka[BatchService],
    attribute_service: FromDishka[AttributeService],
    heartbeat: FromDishka[ImageHeartbeat],
) -> None:
    """Download then pre-process the image with given UID.

    Resumable: a redelivery (or manual retry) re-enters this task and the
    entry guard inspects the image's status to decide whether to run both
    phases, only pre-process, take over from a dead worker, or skip.
    """
    if isinstance(image_uid, str):
        image_uid = UUID(image_uid)
    logger.info(f"Download and pre-process image {image_uid}")

    stale_threshold = datetime.now(timezone.utc) - timedelta(
        seconds=ImageHeartbeat.STALE_AFTER_SECONDS
    )

    with database_service.get_session() as session:
        database_image = database_service.get_image_for_update(session, image_uid)

        if (
            database_image.pre_processed
            or database_image.post_processing
            or database_image.post_processing_failed
            or database_image.post_processed
        ):
            logger.info(
                f"Image {image_uid} already past pre-processing "
                f"(status={database_image.status.name}), skipping"
            )
            return

        if database_image.downloading or database_image.pre_processing:
            heartbeat_ts = database_image.last_heartbeat_at
            if heartbeat_ts is not None and heartbeat_ts >= stale_threshold:
                logger.info(
                    f"Image {image_uid} actively held by another worker "
                    f"(status={database_image.status.name}, fresh heartbeat), skipping"
                )
                return
            logger.warning(
                f"Image {image_uid} has stale heartbeat in "
                f"{database_image.status.name}, taking over"
            )
            if database_image.downloading:
                database_image.reset_as_not_started()
            else:
                database_image.reset_as_downloaded()

        if database_image.not_started:
            database_image.set_as_downloading(task_id=task_id)
            session.commit()
            needs_download = True
        elif database_image.downloaded:
            database_image.set_as_pre_processing(task_id=task_id)
            session.commit()
            needs_download = False
        else:
            logger.info(
                f"Image {image_uid} in non-resumable state "
                f"(status={database_image.status.name}), skipping"
            )
            return

    with heartbeat.track(image_uid):
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
                database_image = database_service.get_image_for_update(
                    session, image_uid
                )
                if not database_image.downloaded:
                    logger.warning(
                        f"Image {image_uid} not in DOWNLOADED after download "
                        f"(status={database_image.status.name}), skipping pre-process"
                    )
                    return
                database_image.set_as_pre_processing(task_id=task_id)
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
)
def post_process_image(
    image_uid: Union[UUID, str],
    task_id: str,
    image_export_interface: FromDishka[ImageExportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    storage_service: FromDishka[StorageService],
    heartbeat: FromDishka[ImageHeartbeat],
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
        database_image.set_as_post_processing(task_id=task_id)
        session.commit()

    project = None
    with heartbeat.track(image_uid), database_service.get_session() as session:
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

            current_task_id = database_service.get_image_for_update(
                session, image_uid
            ).processing_task_id
            if current_task_id != task_id:
                logger.warning(
                    f"Image {image_uid} claimed by another task "
                    f"({current_task_id}), cleaning up"
                )
                storage_service.cleanup_processing_task(project, task_id)
                session.rollback()
                return

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
)
def store_batch_images_to_outbox(
    batch_uid: Union[UUID, str],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    storage_service: FromDishka[StorageService],
    schema_service: FromDishka[SchemaService],
    slidetap_config: FromDishka[SlideTapConfig],
) -> None:
    """Move post-processed images from the processing directory to the outbox."""
    if isinstance(batch_uid, str):
        batch_uid = UUID(batch_uid)
    logger.info(f"Storing batch {batch_uid} images to outbox")
    use_pseudonyms = slidetap_config.use_pseudonyms

    with database_service.get_session(commit=False) as session:
        database_batch = database_service.get_batch(session, batch_uid)
        project = database_batch.project.model

        image_models = []
        for image_schema in schema_service.images.values():
            for database_image in database_service.get_images(
                session,
                schema=image_schema,
                batch=batch_uid,
                selected=True,
                status_filter=[ImageStatus.POST_PROCESSED],
            ):
                image_models.append(database_image.model)

    storage_service.publish_processed_images(project, image_models, use_pseudonyms)

    with database_service.get_session() as session:
        for image_model in image_models:
            database_image = database_service.get_image(session, image_model.uid)
            if image_model.folder_path is not None:
                database_image.folder_path = str(image_model.folder_path)
            if image_model.thumbnail_path is not None:
                database_image.thumbnail_path = str(image_model.thumbnail_path)

        database_batch = database_service.get_batch(session, batch_uid)
        batch_service.set_as_completed(database_batch, session=session)


@dishka_task(
    slidetap_tasks,
    name="remap_batch_attributes",
    queue=TaskQueue.DEFAULT,
    priority=TaskPriority.HIGH,
)
def remap_batch_attributes(
    batch_uid: Union[UUID, str],
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
)
def remap_dataset_attributes(
    dataset_uid: Union[UUID, str],
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
)
def process_metadata_export(
    project_id: Union[UUID, str],
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
)
def process_metadata_import(
    batch_uid: Union[UUID, str],
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
)
def retry_metadata_search_item(
    search_item_uid: Union[UUID, str],
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
            except Exception as exception:
                logger.error(
                    f"Failed to persist retry result for search item {search_item_uid}",
                    exc_info=True,
                )
                search_item_service.mark_failed(
                    search_item_uid, str(exception), session=session
                )
        session.commit()


_RECOVERY_CRON = "0 * * * *"
"""Run periodic self-healing hourly."""


@slidetap_tasks.periodic(cron=_RECOVERY_CRON)
@dishka_task(
    slidetap_tasks,
    name="recover_stuck_images",
    queue=TaskQueue.DEFAULT,
    priority=TaskPriority.HIGH,
)
def recover_stuck_images(
    timestamp: int,
    database_service: FromDishka[DatabaseService],
    storage_service: FromDishka[StorageService],
    app: FromDishka[TaskApp],
) -> None:
    """Reset images whose processing worker has gone silent and re-dispatch."""
    to_redispatch: list[tuple[UUID, ImageStatus]] = []

    with database_service.get_session() as session:
        stuck_images = database_service.get_stuck_processing_images(
            session, ImageHeartbeat.STALE_AFTER_SECONDS
        )
        if not stuck_images:
            return

        for image in stuck_images:
            old_status = image.status
            task_id = image.processing_task_id

            if old_status == ImageStatus.DOWNLOADING:
                image.status = ImageStatus.NOT_STARTED
            elif old_status == ImageStatus.PRE_PROCESSING:
                image.status = ImageStatus.DOWNLOADED
            else:
                image.status = ImageStatus.PRE_PROCESSED

            image.processing_started_at = None
            image.processing_task_id = None
            image.last_heartbeat_at = None

            to_redispatch.append((image.uid, old_status))

            logger.warning(
                f"Reset image {image.uid} from {old_status.name} "
                f"to {image.status.name} (stale heartbeat, dead task_id={task_id})"
            )

            if task_id is not None and image.batch is not None:
                try:
                    project = image.batch.project.model
                    storage_service.cleanup_processing_task(project, task_id)
                except Exception:
                    logger.error(
                        f"Failed to cleanup processing task {task_id} "
                        f"for image {image.uid}",
                        exc_info=True,
                    )

    logger.warning(f"Recovering {len(to_redispatch)} stuck image(s).")

    with app.open():
        for image_uid, original_status in to_redispatch:
            if original_status in (
                ImageStatus.DOWNLOADING,
                ImageStatus.PRE_PROCESSING,
            ):
                download_and_pre_process_image.configure(
                    lock=f"image-{image_uid}",
                ).defer(image_uid=str(image_uid))
            else:
                post_process_image.configure(
                    lock=f"image-{image_uid}",
                ).defer(image_uid=str(image_uid))


@slidetap_tasks.periodic(cron=_RECOVERY_CRON)
@dishka_task(
    slidetap_tasks,
    name="recover_stuck_batches",
    queue=TaskQueue.DEFAULT,
    priority=TaskPriority.HIGH,
)
def recover_stuck_batches(
    timestamp: int,
    database_service: FromDishka[DatabaseService],
    app: FromDishka[TaskApp],
) -> None:
    """Re-dispatch outbox-store for batches stuck in IMAGE_STORING."""
    with database_service.get_session(commit=False) as session:
        stuck_batch_uids: list[UUID] = [
            row.uid
            for row in session.execute(
                select(DatabaseBatch.uid).where(
                    DatabaseBatch.status == BatchStatus.IMAGE_STORING
                )
            ).all()
        ]

    if not stuck_batch_uids:
        return

    logger.warning(f"Found {len(stuck_batch_uids)} batch(es) stuck in IMAGE_STORING.")
    with app.open():
        for batch_uid in stuck_batch_uids:
            store_batch_images_to_outbox.configure(
                lock=f"store-{batch_uid}",
            ).defer(batch_uid=str(batch_uid))
