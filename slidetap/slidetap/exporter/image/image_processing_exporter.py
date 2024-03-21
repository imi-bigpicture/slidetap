from typing import Optional

from flask import Flask

from slidetap.database.project import Image, Project
from slidetap.exporter.image.image_exporter import ImageExporter
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

    def init_app(self, app: Flask):
        super().init_app(app)
        self._post_processor.init_app(app)

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
                self.processor.run,
                {"image_uid": image.uid},
            )
