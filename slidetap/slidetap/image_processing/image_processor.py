"""Metaclass for metadata exporter."""

from abc import ABCMeta, abstractmethod
from uuid import UUID

from slidetap.database import Image
from slidetap.storage import Storage


class ImageProcessor(metaclass=ABCMeta):
    """Metaclass for an image exporter that runs jobs in background threads."""

    def __init__(
        self,
        storage: Storage,
    ):
        self._storage = storage

    @abstractmethod
    def _set_failed_status(self, image: Image) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _set_processing_status(self, image: Image) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _set_processed_status(self, image: Image) -> None:
        raise NotImplementedError()

    @abstractmethod
    def run(self, image_uid: UUID):
        """The action that should be run for a job.

        Parameters
        ----------
        image_uid: UUID
            Identifier for the image to process.

        """
        raise NotImplementedError()
