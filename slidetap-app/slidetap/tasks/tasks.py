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

from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger

from slidetap.tasks.processors import processor_container

logger = get_task_logger(__name__)


@shared_task
def post_process_image(image_uid: UUID):
    logger.info(f"Post processing image {image_uid}")
    processor = processor_container.image_post_processor
    processor.run(image_uid)


@shared_task
def pre_process_image(image_uid: UUID):
    logger.info(f"Pre processing image {image_uid}")
    processor = processor_container.image_pre_processor
    processor.run(image_uid)


@shared_task
def process_metadata_export(project_id: UUID):
    logger.info(f"Exporting metadata for project {project_id}")
    processor = processor_container.metadata_export_processor
    processor.run(project_id)


@shared_task
def process_metadata_import(project_id: UUID, **kwargs):
    logger.info(f"Importing metadata for project {project_id}")
    processor = processor_container.metadata_import_processor
    processor.run(project_id, **kwargs)
