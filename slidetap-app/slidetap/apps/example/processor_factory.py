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

"""Processor factories for example application."""

from slidetap.apps.example.json_metadata_exporter import JsonMetadataExportProcessor
from slidetap.apps.example.metadata_importer import (
    ExampleMetadataImportProcessor,
)
from slidetap.storage import Storage
from slidetap.tasks import (
    CreateThumbnails,
    DicomProcessingStep,
    FinishingStep,
    ImagePostProcessor,
    ImagePreProcessor,
    StoreProcessingStep,
)
from slidetap.tasks.processors.metadata.metadata_export_processor import (
    MetadataExportProcessor,
)
from slidetap.tasks.processors.metadata.metadata_import_processor import (
    MetadataImportProcessor,
)
from slidetap.tasks.processors.processor_factory import ProcessorFactory


class ExampleImagePreProcessorFactory(ProcessorFactory[ImagePreProcessor]):
    def _create(self) -> ImagePreProcessor:
        storage = Storage(self._config.storage_path)
        return ImagePreProcessor(storage)


class ExampleImagePostProcessorFactory(ProcessorFactory[ImagePostProcessor]):
    def _create(self) -> ImagePostProcessor:
        storage = Storage(self._config.storage_path)
        return ImagePostProcessor(
            storage,
            [
                DicomProcessingStep(
                    config=self._config.dicomization_config,
                    use_pseudonyms=False,
                ),
                CreateThumbnails(use_pseudonyms=False),
                StoreProcessingStep(use_pseudonyms=False),
                FinishingStep(),
            ],
        )


class ExampleMetadataExportProcessorFactory(ProcessorFactory[MetadataExportProcessor]):
    def _create(self) -> JsonMetadataExportProcessor:
        storage = Storage(self._config.storage_path)
        return JsonMetadataExportProcessor(storage)


class ExampleMetadataImportProcessorFactory(ProcessorFactory[MetadataImportProcessor]):
    def _create(self) -> ExampleMetadataImportProcessor:
        return ExampleMetadataImportProcessor()
