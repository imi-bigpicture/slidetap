from typing import Optional

from flask import Flask

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

    def init_app(self, app: Flask):
        super().init_app(app)
        self._pre_processor.init_app(app)

    @property
    def processor(self) -> ImageProcessor:
        return self._pre_processor
