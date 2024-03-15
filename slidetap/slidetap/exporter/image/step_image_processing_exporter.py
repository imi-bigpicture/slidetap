from typing import Optional, Sequence

from flask import Flask

from slidetap.exporter.image import ImageProcessingExporter
from slidetap.image_processing.image_processing_step import ImageProcessingStep
from slidetap.image_processing.step_image_processor import ImagePostProcessor
from slidetap.scheduler import Scheduler
from slidetap.storage import Storage


class StepImageProcessingExporter(ImageProcessingExporter):
    """Image exporter that"""

    def __init__(
        self,
        scheduler: Scheduler,
        storage: Storage,
        steps: Sequence[ImageProcessingStep],
        app: Optional[Flask] = None,
    ):
        self._processor = ImagePostProcessor(
            storage,
            steps,
        )
        super().__init__(scheduler, storage, app)

    def init_app(self, app: Flask):
        super().init_app(app)
        self._processor.init_app(app)

    @property
    def processor(self) -> ImagePostProcessor:
        return self._processor
