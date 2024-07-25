from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar

from flask import Flask

from slidetap.config import Config
from slidetap.tasks.processors.image.step_image_processor import (
    ImagePostProcessor,
    ImagePreProcessor,
)
from slidetap.tasks.processors.metadata.metadata_export_processor import (
    MetadataExportProcessor,
)
from slidetap.tasks.processors.metadata.metadata_import_processor import (
    MetadataImportProcessor,
)

ProcessorType = TypeVar(
    "ProcessorType",
    ImagePreProcessor,
    ImagePostProcessor,
    MetadataExportProcessor,
    MetadataImportProcessor,
)


class ProcessorFactory(Generic[ProcessorType], metaclass=ABCMeta):
    """Factory for creating processors."""

    def __init__(self, config: Config):
        """Initialize the factory.

        Parameters
        ----------
        config: Config
            Configuration used when creating processor.
        """
        self._config = config

    @property
    def config(self) -> Config:
        """Configuration for the factory."""
        return self._config

    def create(self, app: Flask) -> ProcessorType:
        """Create and initialize a processor."""
        processor = self._create()
        processor.init_app(app)
        return processor

    @abstractmethod
    def _create(self) -> ProcessorType:
        """Create a processor."""
        raise NotImplementedError()
