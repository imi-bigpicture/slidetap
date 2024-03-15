"""Metaclass for metadata exporter."""

from abc import ABCMeta, abstractmethod
from typing import Optional
from uuid import UUID

from flask import Flask

from slidetap.database.project import Image
from slidetap.flask_extension import FlaskExtension
from slidetap.storage import Storage


class ImageProcessor(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for an image exporter that runs jobs in background threads."""

    def __init__(
        self,
        storage: Storage,
        app: Optional[Flask] = None,
    ):
        self._storage = storage
        super().__init__(app)

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
    def run_job(self, image_uid: UUID):
        """The action that should be run for a job.

        Parameters
        ----------
        image_uid: UUID
            Identifier for the image to process.

        """
        raise NotImplementedError()
