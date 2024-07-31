#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Metaclass for metadata exporter."""

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Iterable, Optional
from uuid import UUID

from flask import Flask, current_app

from slidetap.database import Image, db
from slidetap.model import ImageStatus
from slidetap.storage import Storage
from slidetap.task.processors.image.image_processing_step import (
    ImageProcessingStep,
)
from slidetap.task.processors.processor import Processor


class ImageProcessor(Processor, metaclass=ABCMeta):
    """Image processor that runs a sequence of steps on the processing image."""

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
        """
        if steps is None:
            steps = []
        self._steps = steps
        self._storage = storage
        super().__init__(app)

    def init_app(self, app: Flask):
        for step in self._steps:
            step.init_app(app)
        return super().init_app(app)

    def run(self, image_uid: UUID):
        with self._app.app_context():
            image = Image.get(image_uid)
            current_app.logger.debug(f"Processing image {image.uid}.")
            with db.session.no_autoflush:
                if self._skip_image(image):
                    current_app.logger.debug(
                        f"Skipping image {image.uid} as it is already processed."
                    )
                    return
                self._set_processing_status(image)
                processing_path = Path(image.folder_path)
                try:
                    for step in self._steps:
                        try:
                            processing_path = step.run(
                                self._storage, image, processing_path
                            )
                        except Exception as exception:
                            db.session.rollback()
                            current_app.logger.error(
                                f"Processing failed for {image.uid} name {image.name} "
                                f"at step {step}.",
                                exc_info=True,
                            )
                            image.status_message = (
                                f"Failed during processing at step {step} due to "
                                f"exception {exception}."
                            )
                            self._set_failed_status(image)
                            return
                    current_app.logger.debug(f"Processing complete for {image.uid}.")
                    self._set_processed_status(image)
                    db.session.commit()
                finally:
                    current_app.logger.debug(f"Cleanup {image.uid} name {image.name}.")
                    for step in self._steps:
                        step.cleanup(image)

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
    def _skip_image(self, image: Image) -> bool:
        raise NotImplementedError()


class ImagePostProcessor(ImageProcessor):
    def _set_processing_status(self, image: Image) -> None:
        image.set_as_post_processing()

    def _set_processed_status(self, image: Image) -> None:
        image.set_as_post_processed()
        image.project.set_status_if_all_images_post_processed()

    def _set_failed_status(self, image: Image) -> None:
        image.set_as_post_processing_failed()
        image.select(False)
        image.project.set_status_if_all_images_post_processed()

    def _skip_image(self, image: Image) -> bool:
        return image.status == ImageStatus.POST_PROCESSED


class ImagePreProcessor(ImageProcessor):
    def _set_processing_status(self, image: Image) -> None:
        image.set_as_pre_processing()

    def _set_processed_status(self, image: Image) -> None:
        image.set_as_pre_processed()
        image.project.set_status_if_all_images_pre_processed()

    def _set_failed_status(self, image: Image) -> None:
        image.set_as_pre_processing_failed()
        image.select(False)
        image.project.set_status_if_all_images_pre_processed()

    def _skip_image(self, image: Image) -> bool:
        return image.status == ImageStatus.PRE_PROCESSED
