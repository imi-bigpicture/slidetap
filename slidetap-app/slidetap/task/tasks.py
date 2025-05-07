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

from typing import Any, Dict, Iterable
from uuid import UUID

from celery import chain, group, shared_task

from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.services.database_service import DatabaseService


@shared_task(bind=True)
def download_image(self, image_uid: UUID, **kwargs: Dict[str, Any]):
    self.logger.info(f"Downloading image {image_uid}")
    image_import_interface: ImageImportInterface = self.image_import_interface
    try:
        image_import_interface.download(image_uid, **kwargs)
    except Exception:
        self.logger.error(f"Failed to download image {image_uid}", exc_info=True)


@shared_task(bind=True)
def pre_process_image(self, image_uid: UUID):
    self.logger.info(f"Pre processing image {image_uid}")
    metadata_import_interface: MetadataImportInterface = self.metadata_import_interface
    try:
        metadata_import_interface.import_image_metadata(image_uid)
    except Exception:
        self.logger.error(f"Failed to pre-process image {image_uid}", exc_info=True)


@shared_task(bind=True)
def post_process_image(self, image_uid: UUID):
    self.logger.info(f"Post processing image {image_uid}")
    image_export_interface: ImageExportInterface = self.image_export_interface
    try:
        image_export_interface.export(image_uid)
    except Exception:
        self.logger.error(f"Failed to post-process image {image_uid}", exc_info=True)


@shared_task(bind=True)
def process_metadata_export(self, project_id: UUID):
    self.logger.info(f"Exporting metadata for project {project_id}")
    metadata_export_interface: MetadataExportInterface = self.metadata_export_interface
    try:
        metadata_export_interface.export(project_id)
    except Exception:
        self.logger.error(
            f"Failed to export metadata for project {project_id}", exc_info=True
        )


@shared_task(bind=True)
def process_metadata_import(self, batch_uid: UUID, **kwargs: Dict[str, Any]):
    self.logger.info(f"Importing metadata for batch {batch_uid}")
    metadata_import_interface: MetadataImportInterface = self.metadata_import_interface
    try:
        metadata_import_interface.search(batch_uid, **kwargs)
    except Exception:
        self.logger.error(
            f"Failed to import metadata for batch {batch_uid}", exc_info=True
        )


@shared_task(bind=True)
def get_images_in_batch(
    self, batch_uid: UUID, image_schema_uid, **kwargs: Dict[str, Any]
) -> Iterable[UUID]:
    database_service: DatabaseService = self.database_service
    with database_service.get_session() as session:
        images = database_service.get_images(
            session, batch=batch_uid, schema=image_schema_uid
        )
        image_uids = [image.uid for image in images]
        self.logger.info(
            f"Got {len(image_uids)} images of schema {image_schema_uid} in batch {batch_uid}"
        )
        return image_uids


@shared_task(bind=True)
def get_cases_in_batch(
    self, batch_uid: UUID, case_schema_uid, **kwargs: Dict[str, Any]
) -> Iterable[UUID]:
    self.logger.info(f"Getting images in batch {batch_uid}")
    database_service: DatabaseService = self.database_service
    with database_service.get_session() as session:
        cases = database_service.get_samples(
            session, batch=batch_uid, schema=case_schema_uid
        )
        return [case.uid for case in cases]


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
