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

from slidetap.database import DatabaseImageFile
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.model import ImageStatus
from slidetap.service_provider import ServiceProvider


@shared_task(bind=True)
def download_image(self, image_uid: UUID):
    """Download image with given UID."""
    self.logger.info(f"Downloading image {image_uid}")
    image_import_interface: ImageImportInterface = self.image_import_interface
    service_provider: ServiceProvider = self.service_provider
    database_service = service_provider.database_service
    item_service = service_provider.item_service

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
            self.logger.error(f"Failed to download image {image_uid}", exc_info=True)
            database_image.set_as_downloading_failed()
            item_service.select_image(database_image, False, session=session)


@shared_task(bind=True)
def pre_process_image(self, image_uid: UUID):
    self.logger.info(f"Pre processing image {image_uid}")
    metadata_import_interface: MetadataImportInterface = self.metadata_import_interface
    service_provider: ServiceProvider = self.service_provider
    database_service = service_provider.database_service
    batch_service = service_provider.batch_service
    attribute_service = service_provider.attribute_service
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
            self.logger.error(f"Failed to pre-process image {image_uid}", exc_info=True)
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
            self.logger.debug(
                f"Batch {database_image.batch.uid} not yet finished pre-processing. "
                f"Image {any_non_completed.uid} has status {any_non_completed.status}."
            )
            return
        self.logger.debug(f"Batch {database_image.batch.uid} pre-processed.")
        self.logger.debug(
            f"Batch {database_image.batch.uid} status {database_image.batch.status}."
        )
        batch_service.set_as_pre_processed(database_image.batch, session=session)


@shared_task(bind=True)
def post_process_image(self, image_uid: UUID):
    self.logger.info(f"Post processing image {image_uid}")
    image_export_interface: ImageExportInterface = self.image_export_interface
    service_provider: ServiceProvider = self.service_provider
    database_service = service_provider.database_service
    batch_service = service_provider.batch_service
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
            self.logger.error(
                f"Failed to post-process image {image_uid}", exc_info=True
            )
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
            self.logger.debug(
                f"Batch {database_image.batch.uid} not yet finished post-processing. "
                f"Image {any_non_completed.uid} has status {any_non_completed.status}."
            )
            return
        self.logger.debug(f"Batch {database_image.batch.uid} post-processed.")
        self.logger.debug(
            f"Batch {database_image.batch.uid} status {database_image.batch.status}."
        )
        batch_service.set_as_post_processed(database_image.batch, session=session)


@shared_task(bind=True)
def process_metadata_export(self, project_id: UUID):
    self.logger.info(f"Exporting metadata for project {project_id}")
    metadata_export_interface: MetadataExportInterface = self.metadata_export_interface
    service_provider: ServiceProvider = self.service_provider
    project_service = service_provider.project_service
    database_service = service_provider.database_service
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
            self.logger.error(
                f"Failed to set project {project_id} as exporting", exc_info=True
            )
            project_service.set_as_complete(database_project, session)


@shared_task(bind=True)
def process_metadata_import(self, batch_uid: UUID, search_parameters: Any):
    self.logger.info(f"Importing metadata for batch {batch_uid}")
    metadata_import_interface: MetadataImportInterface = self.metadata_import_interface
    service_provider: ServiceProvider = self.service_provider
    database_service = service_provider.database_service
    batch_service = service_provider.batch_service
    item_service = service_provider.item_service
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
            self.logger.error(
                f"Failed to set batch {batch_uid} as importing", exc_info=True
            )
            batch_service.set_as_failed(database_batch, session)


@shared_task(bind=True)
def get_images_in_batch(self, batch_uid: UUID, image_schema_uid) -> Iterable[UUID]:
    service_provider: ServiceProvider = self.service_provider
    database_service = service_provider.database_service
    with database_service.get_session() as session:
        images = database_service.get_images(
            session, batch=batch_uid, schema=image_schema_uid
        )
        image_uids = [image.uid for image in images]
        self.logger.info(
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
