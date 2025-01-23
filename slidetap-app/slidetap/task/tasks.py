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

from pathlib import Path
from typing import Any, Dict
from uuid import UUID

from celery import shared_task


@shared_task(bind=True)
def download_image(self, image_uid: UUID, **kwargs: Dict[str, Any]):
    self.logger.info(f"Downloading image {image_uid}")
    try:
        self.image_downloader.run(image_uid, **kwargs)
    except Exception:
        self.logger.error(f"Failed to download image {image_uid}", exc_info=True)


@shared_task(bind=True)
def pre_process_image(self, image_uid: UUID):
    self.logger.info(f"Pre processing image {image_uid}")
    try:
        self.image_pre_processor.run(image_uid)
    except Exception:
        self.logger.error(f"Failed to pre-process image {image_uid}", exc_info=True)


@shared_task(bind=True)
def post_process_image(self, image_uid: UUID):
    self.logger.info(f"Post processing image {image_uid}")
    try:
        self.image_post_processor.run(image_uid)
    except Exception:
        self.logger.error(f"Failed to post-process image {image_uid}", exc_info=True)


@shared_task(bind=True)
def process_metadata_export(self, project_id: UUID):
    self.logger.info(f"Exporting metadata for project {project_id}")
    try:
        self.metadata_export_processor.run(project_id)
    except Exception:
        self.logger.error(
            f"Failed to export metadata for project {project_id}", exc_info=True
        )


@shared_task(bind=True)
def process_metadata_import(self, batch_uid: UUID, **kwargs: Dict[str, Any]):
    self.logger.info(f"Importing metadata for batch {batch_uid}")
    try:
        self.metadata_import_processor.run(batch_uid, **kwargs)
    except Exception:
        self.logger.error(
            f"Failed to import metadata for batch {batch_uid}", exc_info=True
        )


@shared_task(bind=True)
def process_dataset_import(self, dataset_path: str, **kwargs: Dict[str, Any]):
    self.logger.info(f"Importing dataset {dataset_path}")
    try:
        self.dataset_import_processor.run(Path(dataset_path), **kwargs)
    except Exception:
        self.logger.error(f"Failed to import dataset {dataset_path}", exc_info=True)
