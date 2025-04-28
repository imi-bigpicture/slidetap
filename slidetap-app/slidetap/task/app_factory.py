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

"""Factory for creating a Celery application with Flask context tasks."""

import logging
from functools import cached_property
from typing import Any, Optional, Sequence, Type

from celery import Celery, Task
from celery.utils.log import get_task_logger

from slidetap.config import Config
from slidetap.logging import setup_logging
from slidetap.service_provider import ServiceProvider
from slidetap.services.database_service import DatabaseService
from slidetap.services.item_service import ItemService
from slidetap.task.processors import (
    ImagePostProcessor,
    ImagePreProcessor,
    MetadataExportProcessor,
    MetadataImportProcessor,
)
from slidetap.task.processors.dataset.dataset_import_processor import (
    DatasetImportProcessor,
)
from slidetap.task.processors.image.image_downloader import ImageDownloader
from slidetap.task.processors.processor_factory import ProcessorFactory


class TaskClassFactory:
    def __init__(
        self,
        service_provider: ServiceProvider,
        image_downloader_factory: Optional[
            ProcessorFactory[ImageDownloader, Any]
        ] = None,
        image_pre_processor_factory: Optional[
            ProcessorFactory[ImagePreProcessor, Any]
        ] = None,
        image_post_processor_factory: Optional[
            ProcessorFactory[ImagePostProcessor, Any]
        ] = None,
        metadata_export_processor_factory: Optional[
            ProcessorFactory[MetadataExportProcessor, Any]
        ] = None,
        metadata_import_processor_factory: Optional[
            ProcessorFactory[MetadataImportProcessor, Any]
        ] = None,
        dataset_import_processor_factory: Optional[
            ProcessorFactory[DatasetImportProcessor, Any]
        ] = None,
    ):
        self.service_provider = service_provider
        self.image_downloader_factory = image_downloader_factory
        self.image_pre_processor_factory = image_pre_processor_factory
        self.image_post_processor_factory = image_post_processor_factory
        self.metadata_export_processor_factory = metadata_export_processor_factory
        self.metadata_import_processor_factory = metadata_import_processor_factory
        self.dataset_import_processor_factory = dataset_import_processor_factory

    def create(self) -> Type[Task]:
        service_provider = self.service_provider
        image_downloader_factory = self.image_downloader_factory
        image_pre_processor_factory = self.image_pre_processor_factory
        image_post_processor_factory = self.image_post_processor_factory
        metadata_export_processor_factory = self.metadata_export_processor_factory
        metadata_import_processor_factory = self.metadata_import_processor_factory
        dataset_import_processor_factory = self.dataset_import_processor_factory
        logging.info("Creating Celery task class.")

        class CustomTask(Task):
            @cached_property
            def logger(self):
                return get_task_logger(self.name)

            @cached_property
            def image_downloader(self) -> ImageDownloader:
                if image_downloader_factory is None:
                    self.logger.error("Image downloader factory not set.")
                    raise ValueError("Image downloader factory not set.")
                self.logger.info("Creating image downloader.")
                return image_downloader_factory.create()

            @cached_property
            def image_pre_processor(self) -> ImagePreProcessor:
                if image_pre_processor_factory is None:
                    self.logger.error("Image pre-processor factory not set.")
                    raise ValueError("Image pre-processor factory not set.")
                self.logger.info("Creating image pre-processor.")
                return image_pre_processor_factory.create()

            @cached_property
            def image_post_processor(self) -> ImagePostProcessor:
                if image_post_processor_factory is None:
                    self.logger.error("Image post-processor factory not set.")
                    raise ValueError("Image post-processor factory not set.")
                self.logger.info("Creating image post-processor.")
                return image_post_processor_factory.create()

            @cached_property
            def metadata_export_processor(self) -> MetadataExportProcessor:
                if metadata_export_processor_factory is None:
                    self.logger.error("Metadata export processor factory not set.")
                    raise ValueError("Metadata export processor factory not set.")
                self.logger.info("Creating metadata export processor.")
                return metadata_export_processor_factory.create()

            @cached_property
            def metadata_import_processor(self) -> MetadataImportProcessor:
                if metadata_import_processor_factory is None:
                    self.logger.error("Metadata import processor factory not set.")
                    raise ValueError("Metadata import processor factory not set.")
                self.logger.info("Creating metadata import processor.")
                return metadata_import_processor_factory.create()

            @cached_property
            def dataset_import_processor(self) -> DatasetImportProcessor:
                if dataset_import_processor_factory is None:
                    self.logger.error("Dataset import processor factory not set.")
                    raise ValueError("Dataset import processor factory not set.")
                self.logger.info("Creating dataset import processor.")
                return dataset_import_processor_factory.create()

            @cached_property
            def database_service(self) -> DatabaseService:
                return service_provider.database_service

        return CustomTask


class SlideTapTaskAppFactory:
    @classmethod
    def create_celery_worker_app(
        cls,
        config: Config,
        task_class_factory: TaskClassFactory,
        name: str,
        include: Optional[Sequence[str]] = None,
    ):
        """Create a Celery application for worker usage."""
        setup_logging(config.flask_log_level)

        logging.info("Creating SlideTap Celery worker app.")
        task_class = task_class_factory.create()

        celery_app = cls._create_celery_app(
            name=name, config=config, task_cls=task_class, include=include
        )
        logging.info("SlideTap Celery worker app created.")
        return celery_app

    @classmethod
    def create_celery_flask_app(
        cls,
        name: str,
        config: Config,
    ):
        """Create a Celery application for flask usage."""
        return cls._create_celery_app(name, config)

    @classmethod
    def _create_celery_app(
        cls,
        name: str,
        config: Config,
        task_cls: Optional[Type[Task]] = None,
        include: Optional[Sequence[str]] = None,
    ):
        """Create a Celery application."""
        if task_cls is None:
            task_cls = Task
        if include is None:
            include = []
        celery_app = Celery(name, task_cls=task_cls, include=include)
        celery_app.config_from_object(config.celery_config)
        celery_app.set_default()
        return celery_app
