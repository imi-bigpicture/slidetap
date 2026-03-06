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

from typing import Any, Iterable
from uuid import UUID

from celery import chain, group, shared_task
from celery.utils.log import get_task_logger
from dishka.integrations.celery import (
    FromDishka,
)

from slidetap.config import SlideTapConfig
from slidetap.database import DatabaseImageFile
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
    ProjectService,
    StorageService,
)
from slidetap.services.schema_service import SchemaService

logger = get_task_logger("tasks")


@shared_task()
def download_image(
    image_uid: UUID,
    image_import_interface: FromDishka[ImageImportInterface],
    database_service: FromDishka[DatabaseService],
    item_service: FromDishka[ItemService],
):
    """Download image with given UID."""
    logger.info(f"Downloading image {image_uid}")

    with database_service.get_session() as session:
        database_image = database_service.get_image(session, image_uid)
        try:
            if database_image.batch is None:
                raise ValueError("Image batch is None")
            database_image.set_as_downloading()
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
        except Exception:
            logger.error(f"Failed to download image {image_uid}", exc_info=True)
            database_image.set_as_downloading_failed()
            item_service.select_image(database_image, False, session=session)


@shared_task(bind=True)
def pre_process_image(
    self,
    image_uid: UUID,
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    attribute_service: FromDishka[AttributeService],
):
    task_id = self.request.id
    logger.info(f"Pre processing image {image_uid}")

    # Atomic entry guard: lock the row, check status, claim or bail
    with database_service.get_session() as session:
        database_image = database_service.get_image_for_update(session, image_uid)

        if not database_image.downloaded:
            logger.info(
                f"Image {image_uid} not in DOWNLOADED state "
                f"(status={database_image.status.name}), skipping"
            )
            session.commit()
            return

        database_image.set_as_pre_processing(task_id=task_id)
        session.commit()

    # Re-fetch without lock for the actual work
    with database_service.get_session() as session:
        database_image = database_service.get_image(session, image_uid)

        try:
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
        except Exception as exception:
            session.rollback()
            logger.error(
                f"Failed to pre-process image {image_uid}", exc_info=True
            )
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

        if database_image.batch is None:
            return
        session.commit()
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
        logger.debug(
            f"Batch {database_image.batch.uid} status {database_image.batch.status}."
        )
        batch_service.set_as_pre_processed(database_image.batch, session=session)


@shared_task(bind=True)
def post_process_image(
    self,
    image_uid: UUID,
    image_export_interface: FromDishka[ImageExportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    storage_service: FromDishka[StorageService],
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
    with database_service.get_session() as session:
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
            logger.error(
                f"Failed to post-process image {image_uid}", exc_info=True
            )
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
                f"Failed to set project {project_id} as exporting", exc_info=True
            )
            project_service.set_as_complete(database_project, session)


@shared_task()
def process_metadata_import(
    batch_uid: UUID,
    search_parameters: Any,
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    item_service: FromDishka[ItemService],
):
    logger.info(f"Importing metadata for batch {batch_uid}")
    with database_service.get_session() as session:
        database_batch = database_service.get_batch(session, batch_uid)
        if not database_batch.metadata_searching:
            return
        mappers = [
            mapper
            for group in database_batch.project.mapper_groups
            for mapper in group.mappers
        ]
        try:
            items = metadata_import_interface.search(
                database_batch.model,
                database_batch.project.dataset.model,
                search_parameters,
            )
            for item in items:
                item_service.add(item, mappers, session=session)
            batch_service.set_as_search_complete(database_batch, session)
        except Exception:
            logger.error(f"Failed to set batch {batch_uid} as importing", exc_info=True)
            batch_service.set_as_failed(database_batch, session)


@shared_task()
def get_images_in_batch(
    batch_uid: UUID,
    image_schema_uid,
    database_service: FromDishka[DatabaseService],
    schema_service: FromDishka[SchemaService],
) -> Iterable[UUID]:
    with database_service.get_session() as session:
        image_schema = schema_service.images[image_schema_uid]
        images = database_service.get_images(
            session,
            schema=image_schema,
            batch=batch_uid,
        )
        image_uids = [image.uid for image in images]
        logger.info(
            f"Got {len(image_uids)} images of schema {image_schema_uid} in batch {batch_uid}"
        )
        return image_uids


@shared_task()
def download_and_pre_process_images(image_uids: Iterable[UUID]):
    """Download and then pre-process each given image."""
    return group(
        chain(
            download_image.si(image_uid),  # type: ignore
            pre_process_image.si(image_uid),  # type: ignore
        )
        for image_uid in image_uids
    ).apply_async()


@shared_task()
def post_process_images(image_uids: Iterable[UUID]):
    """Download and then pre-process each given image."""
    return group(
        post_process_image.si(image_uid) for image_uid in image_uids  # type: ignore
    ).apply_async()
