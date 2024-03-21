from typing import Optional
from uuid import UUID

from flask import Flask

from slidetap.database import db
from slidetap.image_processing import ImagePreProcessor
from slidetap.image_processing.image_processor import ImageProcessor
from slidetap.importer.image.image_importer import ImageImporter
from slidetap.scheduler import Scheduler


class ImageProcessingImporter(ImageImporter):

    def __init__(
        self,
        scheduler: Scheduler,
        pre_processor: ImagePreProcessor,
        app: Optional[Flask] = None,
    ):
        super().__init__(scheduler, app)
        self._pre_processor = pre_processor

    @property
    def processor(self) -> ImageProcessor:
        return self._pre_processor

    def _run_job(self, image_uid: UUID):
        with self._app.app_context():
            with db.session.no_autoflush:
                self.processor.run(image_uid)
