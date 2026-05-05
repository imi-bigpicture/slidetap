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

"""Module with defined celery background tasks."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger
from dishka.integrations.celery import (
    FromDishka,
)

from slidetap.config import SlideTapConfig
from slidetap.database import DatabaseImageFile, DatabaseMetadataSearchItem
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.model import ImageStatus
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    ItemService,
    MetadataSearchItemService,
    ProjectService,
    StorageService,
)
from slidetap.services.schema_service import SchemaService
from slidetap.task.heartbeat import ImageHeartbeat

logger = get_task_logger("tasks")


@shared_task(bind=True, acks_late=True, task_reject_on_worker_lost=True)
def download_and_pre_process_image(
    self,
    image_uid: UUID,
    image_import_interface: FromDishka[ImageImportInterface],
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    item_service: FromDishka[ItemService],
    batch_service: FromDishka[BatchService],
    attribute_service: FromDishka[AttributeService],
    heartbeat: FromDishka[ImageHeartbeat],
):
    """Download then pre-process the image with given UID.

    Resumable: a redelivery (or manual retry) re-enters this task and the
    entry guard inspects the image's status to decide whether to run both
    phases, only pre-process, take over from a dead worker, or skip.
    """
    task_id = self.request.id
    logger.info(f"Download and pre-process image {image_uid}")

    stale_threshold = datetime.now(timezone.utc) - timedelta(
        seconds=ImageHeartbeat.STALE_AFTER_SECONDS
    )

    # Atomic entry guard: lock the row, decide phase, claim or bail.
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
            # downloading_failed / pre_processing_failed: the retry path is
            # responsible for resetting these to a resumable state first.
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
    """Run the download. Returns True on success, False on handled failure."""
    try:
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            if database_image.batch is None:
                raise ValueError("Image batch is None")
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
            try:
                database_image.status_message = str(exception)
                database_image.set_as_downloading_failed()
            except Exception:
                logger.error(
                    f"Also failed to set failure status for {image_uid}, force-setting",
                    exc_info=True,
                )
                database_image.status = ImageStatus.DOWNLOADING_FAILED
                database_image.status_message = str(exception)
                database_image.last_heartbeat_at = None
            item_service.select_image(database_image, False, session=session)
        return False


def _run_pre_process_phase(
    image_uid: UUID,
    task_id: str,
    metadata_import_interface: MetadataImportInterface,
    database_service: DatabaseService,
    attribute_service: AttributeService,
) -> bool:
    """Run pre-processing. Returns True on success, False on handled failure."""
    try:
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            if database_image.batch is None:
                raise ValueError("Image batch is None")
            image = metadata_import_interface.import_image_metadata(
                database_image.model,
                database_image.batch.model,
                database_image.batch.project.model,
                task_id,
            )
            database_image.folder_path = str(image.folder_path)
            database_image.files = set(
                DatabaseImageFile(database_image, image_file.filename)
                for image_file in image.files
            )
            attribute_service.update_for_item(
                database_image, image.attributes.values(), session
            )
            database_image.set_as_pre_processed()
        return True
    except Exception as exception:
        logger.error(f"Failed to pre-process image {image_uid}", exc_info=True)
        with database_service.get_session() as session:
            database_image = database_service.get_image(session, image_uid)
            try:
                database_image.status_message = str(exception)
                database_image.set_as_pre_processing_failed()
            except Exception:
                logger.error(
                    f"Also failed to set failure status for {image_uid}, force-setting",
                    exc_info=True,
                )
                database_image.status = ImageStatus.PRE_PROCESSING_FAILED
                database_image.status_message = str(exception)
                database_image.last_heartbeat_at = None
        return False


@shared_task(bind=True, acks_late=True, task_reject_on_worker_lost=True)
def post_process_image(
    self,
    image_uid: UUID,
    image_export_interface: FromDishka[ImageExportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    storage_service: FromDishka[StorageService],
    heartbeat: FromDishka[ImageHeartbeat],
):
    task_id = self.request.id
    logger.info(f"Post processing image {image_uid}")

    # Atomic entry guard: lock the row, check status, claim or bail
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

    # Re-fetch without lock for the actual work
    project = None
    with heartbeat.track(image_uid), database_service.get_session() as session:
        database_image = database_service.get_image(session, image_uid)

        try:
            if database_image.batch is None:
                raise ValueError("Image batch is None")
            project = database_image.batch.project.model
            image = image_export_interface.export(
                database_image.model,
                database_image.batch.model,
                project,
                task_id=task_id,
            )

            # Collision check: verify we're still the active task
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
            database_image.files = set(
                DatabaseImageFile(database_image, image_file.filename)
                for image_file in image.files
            )
            database_image.format = image.format
            database_image.set_as_post_processed()
        except Exception as exception:
            session.rollback()
            logger.error(f"Failed to post-process image {image_uid}", exc_info=True)
            if project is not None:
                storage_service.cleanup_processing_task(project, task_id)
            try:
                database_image.status_message = str(exception)
                database_image.set_as_post_processing_failed()
            except Exception:
                logger.error(
                    f"Also failed to set failure status for {image_uid}, force-setting",
                    exc_info=True,
                )
                database_image.status = ImageStatus.POST_PROCESSING_FAILED
                database_image.status_message = str(exception)

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
        logger.debug(
            f"Batch {database_image.batch.uid} status {database_image.batch.status}."
        )
        batch_service.set_as_post_processed(database_image.batch, session=session)


@shared_task()
def store_batch_images_to_outbox(
    batch_uid: UUID,
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    storage_service: FromDishka[StorageService],
    schema_service: FromDishka[SchemaService],
    slidetap_config: FromDishka[SlideTapConfig],
):
    """Move post-processed images from the processing directory to the outbox."""
    logger.info(f"Storing batch {batch_uid} images to outbox")
    use_pseudonyms = slidetap_config.use_pseudonyms

    # Phase 1: Read image models and project from DB (short session)
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

    # Phase 2: Move files (no DB session held)
    storage_service.publish_processed_images(project, image_models, use_pseudonyms)

    # Phase 3: Update DB paths and complete batch (short session)
    with database_service.get_session() as session:
        for image_model in image_models:
            database_image = database_service.get_image(session, image_model.uid)
            if image_model.folder_path is not None:
                database_image.folder_path = str(image_model.folder_path)
            if image_model.thumbnail_path is not None:
                database_image.thumbnail_path = str(image_model.thumbnail_path)

        database_batch = database_service.get_batch(session, batch_uid)
        batch_service.set_as_completed(database_batch, session=session)


@shared_task()
def process_metadata_export(
    project_id: UUID,
    metadata_export_interface: FromDishka[MetadataExportInterface],
    project_service: FromDishka[ProjectService],
    database_service: FromDishka[DatabaseService],
):
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


@shared_task()
def process_metadata_import(
    batch_uid: UUID,
    search_parameters: Any,
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    item_service: FromDishka[ItemService],
    search_item_service: FromDishka[MetadataSearchItemService],
):
    """Drive the metadata search.

    For each ``MetadataSearchResult`` yielded by the importer, create one search-item
    row. Failed units are recorded as FAILED with no items persisted;
    successful units have their items persisted in dependency order with
    a per-unit commit (rollback isolated to that unit on persist error).
    """
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

                # Skip results whose entry-level item already exists in the
                # dataset — by reproducible UID first, then by identifier.
                # Re-running a search for the same case shouldn't duplicate
                # rows or attempt cross-batch UID-drifted relation merges.
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
                        for item in result.items:
                            item_service.add(item, mappers, session=session)
                        search_item_service.mark_complete(
                            search_item, result.item_uid, session=session
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


@shared_task()
def retry_metadata_search_item(
    search_item_uid: UUID,
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    item_service: FromDishka[ItemService],
    search_item_service: FromDishka[MetadataSearchItemService],
):
    """Re-run metadata import for a single previously-failed search item.

    The route has already reset the row to NOT_STARTED and incremented
    retry_count. The importer's ``retry_item`` produces a fresh
    ``MetadataSearchResult``; on success we persist its items and link the row, on
    graceful failure we record the new message, on hard exception we
    record the exception message.
    """
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

    # Single session, savepoint for the item-add + mark_complete work.
    # On savepoint rollback the search-item row stays in the outer
    # transaction available for mark_failed.
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
                    for item in result.items:
                        item_service.add(item, mappers, session=session)
                    search_item_service.mark_complete(
                        search_item_uid, result.item_uid, session=session
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
