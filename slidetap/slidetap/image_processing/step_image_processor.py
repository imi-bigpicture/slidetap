from pathlib import Path
from typing import Iterable, Optional
from uuid import UUID

from flask import Flask, current_app

from slidetap.database import db
from slidetap.database.project import Image
from slidetap.image_processing.image_processing_step import ImageProcessingStep
from slidetap.image_processing.image_processor import ImageProcessor
from slidetap.storage.storage import Storage


class StepImageProcessor(ImageProcessor):
    """Image processor that runs a sequence of steps on the processing image."""

    _steps: Iterable[ImageProcessingStep]

    def __init__(
        self,
        storage: Storage,
        steps: Optional[Iterable[ImageProcessingStep]] = None,
        app: Optional[Flask] = None,
    ):
        """Create a StepImageProcessor.

        Parameters
        ----------
        storage: Storage
        steps: Iterable[ImageProcessingStep]
        app: Optional[Flask] = None
        """
        if steps is None:
            steps = []
        self._steps = list(steps)
        super().__init__(storage, app)

    def init_app(self, app: Flask):
        super().init_app(app)
        for step in self._steps:
            step.init_app(app)

    def _run_job(
        self,
        image_uid: UUID,
    ):
        if not isinstance(self._scheduler.app, Flask):
            raise RuntimeError("init_app() must be run before using exporter.")
        with self._scheduler.app.app_context():
            with db.session.no_autoflush:
                image = Image.get(image_uid)
                self._set_processing_status(image)
                current_app.logger.info(f"Processing image {image.uid}.")
                processing_path = Path(image.folder_path)
                for step in self._steps:
                    try:
                        processing_path = step.run(
                            self._storage, image, processing_path
                        )
                    except Exception as exception:
                        current_app.logger.error(
                            f"Processing failed for {image.uid} name {image.name} at step {step}.",
                            exc_info=True,
                        )
                        image.set_as_failed(
                            f"Failed during processing at step {step} due to exception {exception}."
                        )
                current_app.logger.info(f"Cleanup {image.uid} name {image.name}.")
                for step in self._steps:
                    step.cleanup(image)
                self._set_processed_status(image)


class ImagePostProcessor(StepImageProcessor):
    def _set_processing_status(self, image: Image) -> None:
        image.set_as_post_processing()

    def _set_processed_status(self, image: Image) -> None:
        image.set_as_post_processed()
        image.project.set_status_if_all_images_post_processed()


class ImagePreProcessor(StepImageProcessor):
    def _set_processing_status(self, image: Image) -> None:
        image.set_as_pre_processing()

    def _set_processed_status(self, image: Image) -> None:
        image.set_as_pre_processed()
        image.project.set_status_if_all_images_pre_processed()
