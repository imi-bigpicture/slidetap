"""Metaclass for metadata exporter."""
from abc import ABCMeta, abstractmethod
from typing import Optional
from uuid import UUID

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, current_app
from flask_apscheduler import APScheduler

from slidetap.exporter.exporter import Exporter
from slidetap.storage import Storage


class ImageExporter(Exporter, metaclass=ABCMeta):
    """Metaclass for an image exporter that runs jobs in background threads."""

    def __init__(
        self,
        storage: Storage,
        app: Optional[Flask] = None,
    ):
        super().__init__(storage, app)

    def init_app(self, app: Flask):
        """Setup scheduler for finishing slides."""
        super().init_app(app)
        executors = {"default": ThreadPoolExecutor()}

        scheduler = BackgroundScheduler(executors=executors)

        self._scheduler = APScheduler(scheduler=scheduler)

        if self._scheduler.running:
            self._scheduler.shutdown()
        self._scheduler.init_app(app)
        self._scheduler.start()

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
