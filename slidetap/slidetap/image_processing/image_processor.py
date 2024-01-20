"""Metaclass for metadata exporter."""
from abc import ABCMeta, abstractmethod
from typing import Optional
from uuid import UUID

from apscheduler.job import Job
from flask import Flask, current_app

from slidetap.database.project import Image
from slidetap.scheduler import Scheduler
from slidetap.storage import Storage


class ImageProcessor(Scheduler, metaclass=ABCMeta):
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

    def add_job(self, image_uid: UUID) -> Optional[Job]:
        """Add a job for the image exporter to run.

        Parameters
        ----------
        image_uid: UUID
            Identifier for the image to process.

        Returns
        ----------
        Job
            The created job.
        """
        current_app.logger.info(f"Adding job for image {image_uid}")
        return self._scheduler.add_job(
            func=self._run_job,
            trigger=None,
            misfire_grace_time=None,
            coalesce=False,
            id=str(image_uid),
            args=[image_uid],
        )

    @abstractmethod
    def _run_job(self, image_uid: UUID):
        """The action that should be run for a job.

        Parameters
        ----------
        image_uid: UUID
            Identifier for the image to process.

        """
        raise NotImplementedError()
