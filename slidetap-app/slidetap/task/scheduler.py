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

"""Module with schedulers used for calling execution of defined background tasks."""

import logging
from pathlib import Path
from typing import Any, Dict

from celery import chain

from slidetap.model.batch import Batch
from slidetap.model.item import Image
from slidetap.model.project import Project
from slidetap.task.tasks import (
    download_image,
    post_process_image,
    pre_process_image,
    process_dataset_import,
    process_metadata_export,
    process_metadata_import,
)


class Scheduler:
    """Scheduler that uses Celery to run tasks."""

    def download_image(self, image: Image, **kwargs: Dict[str, Any]):
        logging.info(f"Downloading image {image.uid}")
        try:
            download_image.delay(image.uid, **kwargs)  # type: ignore
        except Exception:
            logging.error(f"Error downloading image {image.uid}", exc_info=True)

    def download_and_pre_process_image(self, image: Image, **kwargs: Dict[str, Any]):
        logging.info(f"Downloading and pre-processing image {image.uid}")

        try:
            chaining = chain(
                download_image.si(image.uid, **kwargs),  # type: ignore
                pre_process_image.si(image.uid),  # type: ignore
            )
            chaining.apply_async()
        except Exception:
            logging.error(
                f"Error downloading and pre-processing image {image.uid}", exc_info=True
            )

    def pre_process_image(self, image: Image):
        logging.info(f"Pre processing image {image.uid}")
        try:
            pre_process_image.delay(image.uid)  # type: ignore
        except Exception:
            logging.error(f"Error pre-processing image {image.uid}", exc_info=True)

    def post_process_image(self, image: Image):
        logging.info(f"Post processing image {image.uid}")
        try:
            post_process_image.delay(image.uid)  # type: ignore
        except Exception:
            logging.error(f"Error post-processing image {image.uid}", exc_info=True)

    def metadata_project_export(self, project: Project):
        logging.info(f"Exporting metadata for project {project.uid}")
        try:
            process_metadata_export.delay(project.uid)  # type: ignore
        except Exception:
            logging.error(
                f"Error exporting metadata for project {project.uid}", exc_info=True
            )

    def metadata_batch_import(
        self,
        batch: Batch,
        **kwargs: Dict[str, Any],
    ):
        logging.info(f"Importing metadata for batch {batch.uid}")
        try:
            process_metadata_import.delay(batch.uid, **kwargs)  # type: ignore
        except Exception:
            logging.error(
                f"Error importing metadata for batch {batch.uid}", exc_info=True
            )

    def dataset_import(self, dataset_path: Path, **kwargs: Dict[str, Any]):
        logging.info(f"Importing dataset {dataset_path}")
        try:
            process_dataset_import.delay(str(dataset_path), **kwargs)  # type: ignore
        except Exception:
            logging.error(f"Error importing dataset {dataset_path}", exc_info=True)
