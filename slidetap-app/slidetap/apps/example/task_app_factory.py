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

"""Celery app factory for example application."""

from typing import Optional

from celery import Celery
from dishka import make_container
from slidetap.apps.example.config import ExampleConfig
from slidetap.apps.example.interfaces import (
    ExampleImageExportInterface,
    ExampleImageImportInterface,
    ExampleMetadataExportInterface,
    ExampleMetadataImportInterface,
)
from slidetap.apps.example.interfaces.image_export import ExampleImagePostProcessor
from slidetap.apps.example.interfaces.metadata_import import ExampleImagePreProcessor
from slidetap.apps.example.schema import ExampleSchema
from slidetap.service_provider import BaseProvider
from slidetap.task import SlideTapTaskAppFactory
from slidetap.task.service_provider import TaskAppProvider


def make_celery(config: Optional[ExampleConfig] = None) -> Celery:
    if config is None:
        config = ExampleConfig()
    base_provider = BaseProvider(
        config=config,
        schema=ExampleSchema(),
        metadata_export_interface=ExampleMetadataExportInterface,
        metadata_import_interface=ExampleMetadataImportInterface,
    )
    task_provider = TaskAppProvider(
        image_export_interface=ExampleImageExportInterface,
        image_import_interface=ExampleImageImportInterface,
    )
    task_provider.provide(ExampleImagePostProcessor)
    task_provider.provide(ExampleImagePreProcessor)
    container = make_container(base_provider, task_provider)

    return SlideTapTaskAppFactory.create_celery_worker_app(
        name=__name__, config=config, container=container
    )
