from abc import abstractmethod
from typing import Optional
from uuid import UUID

from flask import Flask

from slidetap.database import db
from slidetap.database.project import Image, Project
from slidetap.exporter.image.image_exporter import ImageExporter
from slidetap.image_processing.image_processor import ImageProcessor
from slidetap.image_processing.step_image_processor import ImagePostProcessor
from slidetap.scheduler import Scheduler
from slidetap.storage.storage import Storage


class ImageProcessingExporter(ImageExporter):
    def __init__(
        self,
        scheduler: Scheduler,
        post_processor: ImagePostProcessor,
        storage: Storage,
        app: Optional[Flask] = None,
    ):
        self._post_processor = post_processor
        super().__init__(scheduler, storage, app)

    @property
    def processor(self) -> ImagePostProcessor:
        return self._post_processor

    def export(self, project: Project):
        """Should export the image to storage."""
        project.set_as_post_processing()
        images = Image.get_for_project(project.uid)
        for image in images:
            self._scheduler.add_job(
                str(image.uid),
                self._run_job,
                {"image_uid": image.uid},
            )

    def _run_job(self, image_uid: UUID):
        with self._app.app_context():
            with db.session.no_autoflush:
                self.processor.run(image_uid)
