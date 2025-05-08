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
from slidetap.apps.example.config import ExampleConfig
from slidetap.apps.example.interfaces import (
    ExampleImageExportInterface,
    ExampleImageImportInterface,
    ExampleMetadataExportInterface,
    ExampleMetadataImportInterface,
)
from slidetap.apps.example.schema import ExampleSchema
from slidetap.service_provider import ServiceProvider
from slidetap.task import SlideTapTaskAppFactory


def make_celery(
    root_schema: ExampleSchema, config: Optional[ExampleConfig] = None
) -> Celery:
    if config is None:
        config = ExampleConfig()

    service_provider = ServiceProvider(config, root_schema)
    metadata_import_interface = ExampleMetadataImportInterface(service_provider)
    metadata_export_interface = ExampleMetadataExportInterface(service_provider)
    image_import_interface = ExampleImageImportInterface(config)
    image_export_interface = ExampleImageExportInterface(service_provider, config)
    celery = SlideTapTaskAppFactory.create_celery_worker_app(
        config,
        service_provider=service_provider,
        metadata_import_interface=metadata_import_interface,
        metadata_export_interface=metadata_export_interface,
        image_import_interface=image_import_interface,
        image_export_interface=image_export_interface,
        name=__name__,
    )
    return celery
