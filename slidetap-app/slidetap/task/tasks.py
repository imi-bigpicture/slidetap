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

from logging import Logger
from typing import Any, Iterable
from uuid import UUID

from celery import chain, group, shared_task
from celery.utils.log import get_task_logger
from dishka.integrations.celery import (
    FromDishka,
)

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
)

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
            assert database_image.batch is not None
            database_image.set_as_downloading()
            image_folder, image_files = image_import_interface.download(
                database_image.model, database_image.batch.project.model
            )
            database_image.folder_path = str(image_folder)
            for image_file in image_files:
                database_image_file = DatabaseImageFile(database_image, image_file.name)
                session.add(database_image_file)
                database_image.files.append(database_image_file)
            database_image.set_as_downloaded()
        except Exception:
            logger.error(f"Failed to download image {image_uid}", exc_info=True)
            database_image.set_as_downloading_failed()
            item_service.select_image(database_image, False, session=session)


@shared_task()
def pre_process_image(
    image_uid: UUID,
    metadata_import_interface: FromDishka[MetadataImportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
    attribute_service: FromDishka[AttributeService],
):
    logger.info(f"Pre processing image {image_uid}")
    with database_service.get_session() as session:
        database_image = database_service.get_image(session, image_uid)
        if not database_image.downloaded:
            return
        database_image.set_as_pre_processing()
        session.commit()
        try:
            assert database_image.batch is not None
            image = metadata_import_interface.import_image_metadata(
                database_image.model,
                database_image.batch.model,
                database_image.batch.project.model,
            )
            database_image.folder_path = str(image.folder_path)
            database_image.files = [
                DatabaseImageFile(database_image, image_file.filename)
                for image_file in image.files
            ]
            attribute_service.update_for_item(database_image, image.attributes, session)
            database_image.set_as_pre_processed()
        except Exception as exception:
            session.rollback()
            logger.error(f"Failed to pre-process image {image_uid}", exc_info=True)
            database_image.status_message = str(exception)
            database_image.set_as_pre_processing_failed()
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


@shared_task()
def post_process_image(
    image_uid: UUID,
    image_export_interface: FromDishka[ImageExportInterface],
    database_service: FromDishka[DatabaseService],
    batch_service: FromDishka[BatchService],
):
    logger.info(f"Post processing image {image_uid}")
    with database_service.get_session() as session:
        database_image = database_service.get_image(session, image_uid)
        if not database_image.pre_processed:
            return

        database_image.set_as_post_processing()
        session.commit()
        try:
            assert database_image.batch is not None
            image = image_export_interface.export(
                database_image.model,
                database_image.batch.model,
                database_image.batch.project.model,
            )
            database_image.folder_path = str(image.folder_path)
            database_image.files = [
                DatabaseImageFile(database_image, image_file.filename)
                for image_file in image.files
            ]
            database_image.set_as_post_processed()
        except Exception as exception:
            session.rollback()
            logger.error(f"Failed to post-process image {image_uid}", exc_info=True)
            database_image.status_message = str(exception)
            database_image.set_as_post_processing_failed()
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
        try:
            items = metadata_import_interface.search(
                database_batch.model,
                database_batch.project.dataset.model,
                search_parameters,
            )
            for item in items:
                item_service.add(item, session=session)
            batch_service.set_as_search_complete(database_batch, session)
        except Exception:
            logger.error(f"Failed to set batch {batch_uid} as importing", exc_info=True)
            batch_service.set_as_failed(database_batch, session)


@shared_task()
def get_images_in_batch(
    batch_uid: UUID,
    image_schema_uid,
    database_service: FromDishka[DatabaseService],
) -> Iterable[UUID]:
    with database_service.get_session() as session:
        images = database_service.get_images(
            session, batch=batch_uid, schema=image_schema_uid
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
