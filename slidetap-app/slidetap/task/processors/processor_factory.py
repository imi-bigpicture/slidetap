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

import logging
from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar

from slidetap.config import Config
from slidetap.service_provider import ServiceProvider
from slidetap.services.schema_service import SchemaType
from slidetap.task.processors.dataset.dataset_import_processor import (
    DatasetImportProcessor,
)
from slidetap.task.processors.image.image_downloader import ImageDownloader
from slidetap.task.processors.image.image_processor import (
    ImagePostProcessor,
    ImagePreProcessor,
)
from slidetap.task.processors.metadata.metadata_export_processor import (
    MetadataExportProcessor,
)
from slidetap.task.processors.metadata.metadata_import_processor import (
    MetadataImportProcessor,
)

ProcessorType = TypeVar("ProcessorType")

ConfigType = TypeVar("ConfigType", bound=Config, covariant=True)


class ProcessorFactory(
    Generic[ProcessorType, ConfigType, SchemaType], metaclass=ABCMeta
):
    """Factory for creating processors for running tasks in background."""

    def __init__(
        self,
        config: ConfigType,
        service_provider: ServiceProvider[SchemaType],
    ) -> None:
        """Initialize the factory.

        Parameters
        ----------
        config: Config
            Configuration used when creating processor.
        """
        self._config = config
        self._service_provider = service_provider
        self._root_schema = service_provider.schema_service.root

    @property
    def config(self) -> ConfigType:
        """Configuration for the factory."""
        return self._config

    @property
    def service_provider(self) -> ServiceProvider:
        """Service provider for the factory."""
        return self._service_provider

    def create(self) -> ProcessorType:
        """Create a processor."""
        logging.debug("Creating processor.")
        processor = self._create()
        logging.debug("Processor created.")
        return processor

    @abstractmethod
    def _create(self) -> ProcessorType:
        """Override in subclass to create the processor."""
        raise NotImplementedError()


class ImageDownloaderFactory(ProcessorFactory[ImageDownloader, ConfigType, SchemaType]):
    """Factory for creating image downloaders."""


class ImagePreProcessorFactory(
    ProcessorFactory[ImagePreProcessor, ConfigType, SchemaType]
):
    """Factory for creating image pre processors."""


class ImagePostProcessorFactory(
    ProcessorFactory[ImagePostProcessor, ConfigType, SchemaType]
):
    """Factory for creating image post processors."""


class MetadataExportProcessorFactory(
    ProcessorFactory[MetadataExportProcessor, ConfigType, SchemaType]
):
    """Factory for creating metadata export processors."""


class MetadataImportProcessorFactory(
    ProcessorFactory[MetadataImportProcessor, ConfigType, SchemaType]
):
    """Factory for creating metadata import processors."""


class DatasetImportProcessorFactory(
    ProcessorFactory[DatasetImportProcessor, ConfigType, SchemaType]
):
    """Factory for creating dataset import processors."""
