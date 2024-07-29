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

from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Optional

from flask import current_app

from slidetap.database.project import Image, Project
from slidetap.tasks.processors.image.step_image_processor import (
    ImagePostProcessor,
    ImagePreProcessor,
)
from slidetap.tasks.processors.metadata.metadata_export_processor import (
    MetadataExportProcessor,
)
from slidetap.tasks.processors.metadata.metadata_import_processor import (
    MetadataImportProcessor,
)
from slidetap.tasks.processors.processor_factory import ProcessorFactory
from slidetap.tasks.tasks import (
    post_process_image,
    pre_process_image,
    process_metadata_export,
    process_metadata_import,
)


class Queue(Enum):
    """Priority queue for the scheduler."""

    DEFAULT = "default"
    HIGH = "high"


class Scheduler(metaclass=ABCMeta):
    @abstractmethod
    def post_process_image(self, image: Image):
        raise NotImplementedError()

    @abstractmethod
    def pre_process_image(self, image: Image):
        raise NotImplementedError()

    @abstractmethod
    def metadata_project_export(self, project: Project):
        raise NotImplementedError()

    @abstractmethod
    def metadata_project_import(self, project: Project, **kwargs):
        raise NotImplementedError()


class CeleryScheduler(Scheduler):
    """Scheduler that uses Celery to run tasks."""

    def post_process_image(self, image: Image):
        current_app.logger.info(f"Post processing image {image.uid}")
        post_process_image.delay(image.uid)  # type: ignore

    def pre_process_image(self, image: Image):
        current_app.logger.info(f"Pre processing image {image.uid}")
        pre_process_image.delay(image.uid)  # type: ignore

    def metadata_project_export(self, project: Project):
        current_app.logger.info(f"Exporting metadata for project {project.uid}")
        process_metadata_export.delay(project.uid)  # type: ignore

    def metadata_project_import(self, project: Project, **kwargs):
        current_app.logger.info(f"Importing metadata for project {project.uid}")
        process_metadata_import.delay(project.uid, **kwargs)  # type: ignore


class BlockingScheduler(Scheduler):
    """Scheduler that blocks to run tasks. Only use for testing"""

    def __init__(
        self,
        image_pre_processor_factory: Optional[
            ProcessorFactory[ImagePreProcessor]
        ] = None,
        image_post_processor_factory: Optional[
            ProcessorFactory[ImagePostProcessor]
        ] = None,
        metadata_export_processor_factory: Optional[
            ProcessorFactory[MetadataExportProcessor]
        ] = None,
        metadata_import_processor_factory: Optional[
            ProcessorFactory[MetadataImportProcessor]
        ] = None,
    ):
        self._image_pre_processor_factory = image_pre_processor_factory
        self._image_post_processor_factory = image_post_processor_factory
        self._metadata_export_processor_factory = metadata_export_processor_factory
        self._metadata_import_processor_factory = metadata_import_processor_factory

    def post_process_image(self, image: Image):
        current_app.logger.info(f"Post processing image {image.uid}")
        if self._image_post_processor_factory is None:
            raise ValueError("Image post-processor factory not set.")
        self._image_post_processor_factory.create(current_app).run(image.uid)

    def pre_process_image(self, image: Image):
        current_app.logger.info(f"Pre processing image {image.uid}")
        if self._image_pre_processor_factory is None:
            raise ValueError("Image pre-processor factory not set.")
        self._image_pre_processor_factory.create(current_app).run(image.uid)

    def metadata_project_export(self, project: Project):
        current_app.logger.info(f"Exporting metadata for project {project.uid}")
        if self._metadata_export_processor_factory is None:
            raise ValueError("Metadata export processor factory not set.")
        self._metadata_export_processor_factory.create(current_app).run(project.uid)

    def metadata_project_import(self, project: Project, **kwargs):
        current_app.logger.info(f"Importing metadata for project {project.uid}")
        if self._metadata_import_processor_factory is None:
            raise ValueError("Metadata import processor factory not set.")
        self._metadata_import_processor_factory.create(current_app).run(
            project.uid, **kwargs
        )
