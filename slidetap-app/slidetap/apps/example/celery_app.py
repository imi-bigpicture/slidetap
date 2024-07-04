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

"""Flask app factory for example application."""

from typing import Optional

from celery import Celery
from slidetap.apps.example.json_metadata_exporter import JsonMetadataExportProcessor
from slidetap.apps.example.metadata_importer import (
    ExampleMetadataImportProcessor,
)
from slidetap.config import Config, ConfigTest
from slidetap.storage import Storage
from slidetap.tasks import (
    CreateThumbnails,
    DicomProcessingStep,
    FinishingStep,
    ImagePostProcessor,
    ImagePreProcessor,
    SlideTapCeleryAppFactory,
    StoreProcessingStep,
)


def make_celery(config: Optional[Config] = None) -> Celery:
    if config is None:
        config = Config()
    storage = Storage(config.storage_path)
    image_pre_processor = ImagePreProcessor(storage)
    image_post_processor = ImagePostProcessor(
        storage,
        [
            DicomProcessingStep(use_pseudonyms=False),
            CreateThumbnails(use_pseudonyms=False),
            StoreProcessingStep(use_pseudonyms=False),
            FinishingStep(),
        ],
    )
    metadata_export_processor = JsonMetadataExportProcessor(storage)
    metadata_import_processor = ExampleMetadataImportProcessor()

    celery = SlideTapCeleryAppFactory.create(
        image_pre_processor,
        image_post_processor,
        metadata_export_processor,
        metadata_import_processor,
        config,
    )
    return celery


celery_app = make_celery()
