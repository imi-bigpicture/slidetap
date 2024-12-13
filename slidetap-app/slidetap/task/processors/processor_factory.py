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

from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar

from flask import Flask

from slidetap.config import Config
from slidetap.model.schema.root_schema import RootSchema
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
from slidetap.task.processors.processor import Processor

ProcessorType = TypeVar("ProcessorType", bound=Processor)

ConfigType = TypeVar("ConfigType", bound=Config)


class ProcessorFactory(Generic[ProcessorType, ConfigType], metaclass=ABCMeta):
    """Factory for creating processors for running tasks in background."""

    def __init__(self, config: ConfigType, root_schema: RootSchema) -> None:
        """Initialize the factory.

        Parameters
        ----------
        config: Config
            Configuration used when creating processor.
        """
        self._config = config
        self._root_schema = root_schema

    @property
    def config(self) -> ConfigType:
        """Configuration for the factory."""
        return self._config

    def create(self, app: Flask) -> ProcessorType:
        """Create and initialize a processor."""
        app.logger.debug("Creating processor.")
        processor = self._create()
        app.logger.debug("Initializing processor.")
        processor.init_app(app)
        app.logger.debug("Processor created.")
        return processor

    @abstractmethod
    def _create(self) -> ProcessorType:
        """Override in subclass to create the processor."""
        raise NotImplementedError()


class ImageDownloaderFactory(ProcessorFactory[ImageDownloader, ConfigType]):
    """Factory for creating image downloaders."""


class ImagePreProcessorFactory(ProcessorFactory[ImagePreProcessor, ConfigType]):
    """Factory for creating image pre processors."""


class ImagePostProcessorFactory(ProcessorFactory[ImagePostProcessor, ConfigType]):
    """Factory for creating image post processors."""


class MetadataExportProcessorFactory(
    ProcessorFactory[MetadataExportProcessor, ConfigType]
):
    """Factory for creating metadata export processors."""


class MetadataImportProcessorFactory(
    ProcessorFactory[MetadataImportProcessor, ConfigType]
):
    """Factory for creating metadata import processors."""
