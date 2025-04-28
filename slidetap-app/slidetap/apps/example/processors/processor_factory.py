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


from slidetap.apps.example.config import ExampleConfig
from slidetap.apps.example.processors.dataset_import_processor import (
    ExampleDatasetImportProcessor,
)
from slidetap.apps.example.processors.image_downloader import ExampleImageDownloader
from slidetap.apps.example.processors.metadata_export_processor import (
    JsonMetadataExportProcessor,
)
from slidetap.apps.example.processors.metadata_import_processor import (
    ExampleMetadataImportProcessor,
)
from slidetap.config import Config
from slidetap.task import (
    CreateThumbnails,
    DicomProcessingStep,
    FinishingStep,
    ImagePostProcessor,
    ImagePreProcessor,
    StoreProcessingStep,
)
from slidetap.task.processors.processor_factory import (
    DatasetImportProcessorFactory,
    ImageDownloaderFactory,
    ImagePostProcessorFactory,
    ImagePreProcessorFactory,
    MetadataExportProcessorFactory,
    MetadataImportProcessorFactory,
)


class ExampleImageDownloaderFactory(ImageDownloaderFactory[ExampleConfig]):
    def _create(self) -> ExampleImageDownloader:
        image_folder = self._config.example_test_data_path
        image_extension = self._config.example_test_data_image_extension
        return ExampleImageDownloader(
            self._service_provider, image_folder, image_extension
        )


class ExampleImagePreProcessorFactory(ImagePreProcessorFactory[Config]):
    def _create(self) -> ImagePreProcessor:
        return ImagePreProcessor(self._service_provider)


class ExampleImagePostProcessorFactory(ImagePostProcessorFactory[Config]):
    def _create(self) -> ImagePostProcessor:
        return ImagePostProcessor(
            self._service_provider,
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


class ExampleMetadataExportProcessorFactory(MetadataExportProcessorFactory[Config]):
    def _create(self) -> JsonMetadataExportProcessor:
        return JsonMetadataExportProcessor(self._service_provider)


class ExampleMetadataImportProcessorFactory(MetadataImportProcessorFactory[Config]):
    def _create(self) -> ExampleMetadataImportProcessor:
        return ExampleMetadataImportProcessor(self._service_provider)


class ExampleDatasetImportProcessorFactory(DatasetImportProcessorFactory[Config]):
    def _create(self) -> ExampleDatasetImportProcessor:
        return ExampleDatasetImportProcessor(self._service_provider)
