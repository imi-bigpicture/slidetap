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
from slidetap.apps.example.processors.processor_factory import (
    ExampleDatasetImportProcessorFactory,
    ExampleImageDownloaderFactory,
    ExampleImagePostProcessorFactory,
    ExampleImagePreProcessorFactory,
    ExampleMetadataExportProcessorFactory,
    ExampleMetadataImportProcessorFactory,
)
from slidetap.model.schema.root_schema import RootSchema
from slidetap.task import SlideTapTaskAppFactory, TaskClassFactory


def make_celery(
    root_schema: RootSchema, config: Optional[ExampleConfig] = None
) -> Celery:
    if config is None:
        config = ExampleConfig()
    celery_task_class_factory = TaskClassFactory(
        image_downloader_factory=ExampleImageDownloaderFactory(config, root_schema),
        image_pre_processor_factory=ExampleImagePreProcessorFactory(
            config, root_schema
        ),
        image_post_processor_factory=ExampleImagePostProcessorFactory(
            config, root_schema
        ),
        metadata_export_processor_factory=ExampleMetadataExportProcessorFactory(
            config, root_schema
        ),
        metadata_import_processor_factory=ExampleMetadataImportProcessorFactory(
            config, root_schema
        ),
        dataset_import_processor_factory=ExampleDatasetImportProcessorFactory(
            config, root_schema
        ),
    )
    celery = SlideTapTaskAppFactory.create_celery_worker_app(
        config, celery_task_class_factory, __name__
    )
    return celery
