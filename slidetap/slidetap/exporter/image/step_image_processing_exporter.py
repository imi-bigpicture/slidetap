from typing import Optional, Sequence

from flask import Flask
from slidetap.exporter.image import ImageProcessingExporter
from slidetap.image_processing.image_processing_step import ImageProcessingStep
from slidetap.image_processing.step_image_processor import ImagePostProcessor
from slidetap.storage import Storage


class StepImageProcessingExporter(ImageProcessingExporter):
    """Image exporter that"""

    def __init__(
        self,
        storage: Storage,
        steps: Sequence[ImageProcessingStep],
        app: Optional[Flask] = None,
    ):
        super().__init__(storage, app)
        self._processor = ImagePostProcessor(
            self.storage,
            steps,
        )

    def init_app(self, app: Flask):
        super().init_app(app)
        self._processor.init_app(app)

    @property
    def processor(self) -> ImagePostProcessor:
        return self._processor
