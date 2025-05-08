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
from typing import Optional, Sequence, Type

from celery import Celery, Task
from celery.utils.log import get_task_logger

from slidetap.config import Config
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.logging import setup_logging
from slidetap.service_provider import ServiceProvider


class SlideTapTaskAppFactory:
    @classmethod
    def create_celery_worker_app(
        cls,
        config: Config,
        service_provider: ServiceProvider,
        metadata_import_interface: MetadataImportInterface,
        metadata_export_interface: MetadataExportInterface,
        image_import_interface: ImageImportInterface,
        image_export_interface: ImageExportInterface,
        name: str,
        include: Optional[Sequence[str]] = None,
    ):
        """Create a Celery application for worker usage."""
        setup_logging(config.flask_log_level)

        logging.info("Creating SlideTap Celery worker app.")
        task_class = cls._create_task_class(
            service_provider,
            metadata_import_interface,
            metadata_export_interface,
            image_import_interface,
            image_export_interface,
        )

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

    @staticmethod
    def _create_task_class(
        service_provider: ServiceProvider,
        metadata_import_interface: MetadataImportInterface,
        metadata_export_interface: MetadataExportInterface,
        image_import_interface: ImageImportInterface,
        image_export_interface: ImageExportInterface,
    ) -> Type[Task]:

        logging.info("Creating Celery task class.")

        class CustomTask(Task):
            @cached_property
            def logger(self):
                return get_task_logger(self.name)

            @property
            def image_import_interface(self) -> ImageImportInterface:
                return image_import_interface

            @property
            def image_export_interface(self) -> ImageExportInterface:
                return image_export_interface

            @property
            def metadata_import_interface(self) -> MetadataImportInterface:
                return metadata_import_interface

            @property
            def metadata_export_interface(self) -> MetadataExportInterface:
                return metadata_export_interface

            @property
            def service_provider(self) -> ServiceProvider:
                return service_provider

        return CustomTask
