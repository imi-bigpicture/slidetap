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

from slidetap.database import DatabaseImage, DatabaseImageFile, db
from slidetap.model import ImageStatus
from slidetap.model.item import Image
from slidetap.model.schema.root_schema import RootSchema
from slidetap.storage import Storage
from slidetap.task.processors.image.image_processing_step import (
    ImageProcessingStep,
)
from slidetap.task.processors.processor import Processor


class ImageProcessor(Processor, metaclass=ABCMeta):
    """Image processor that runs a sequence of steps on the processing image."""

    def __init__(
        self,
        root_schema: RootSchema,
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
        super().__init__(root_schema, app)

    def run(self, image_uid: UUID):
        with self._app.app_context():
            database_image = self._database_service.get_image(image_uid)
            project = self._database_service.get_project(
                database_image.project_uid
            ).model
            image = database_image.model
            current_app.logger.debug(f"Processing image {image.uid}.")
            with db.session.no_autoflush:
                if self._skip_image(image):
                    current_app.logger.debug(
                        f"Skipping image {image.uid} as it is already processed."
                    )
                    return
                if image.folder_path is None:
                    self._set_failed_status(database_image)
                    db.session.commit()
                    current_app.logger.error(
                        f"Image {image.uid} does not have a folder path."
                    )
                    return
                self._set_processing_status(database_image)
                processing_path = Path(image.folder_path)
                try:
                    for step in self._steps:
                        try:
                            processing_path, image = step.run(
                                self._root_schema,
                                self._storage,
                                project,
                                image,
                                processing_path,
                            )
                        except Exception as exception:
                            db.session.rollback()
                            current_app.logger.error(
                                f"Processing failed for {image.uid} name {image.name} "
                                f"at step {step}.",
                                exc_info=True,
                            )
                            database_image.status_message = (
                                f"Failed during processing at step {step} due to "
                                f"exception {exception}."
                            )
                            self._set_failed_status(database_image)

                            db.session.commit()
                            return
                    current_app.logger.debug(f"Processing complete for {image.uid}.")
                    database_image.folder_path = str(processing_path)
                    database_image.files = [
                        DatabaseImageFile(file.filename) for file in image.files
                    ]
                    if image.thumbnail_path is not None:
                        database_image.thumbnail_path = image.thumbnail_path
                    self._set_processed_status(database_image)
                    db.session.commit()
                finally:
                    current_app.logger.debug(f"Cleanup {image.uid} name {image.name}.")
                    for step in self._steps:
                        step.cleanup(project, image)

    @abstractmethod
    def _set_failed_status(self, image: DatabaseImage) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _set_processing_status(self, image: DatabaseImage) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _set_processed_status(self, image: DatabaseImage) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _skip_image(self, image: Image) -> bool:
        raise NotImplementedError()


class ImagePostProcessor(ImageProcessor):
    def _set_processing_status(self, image: DatabaseImage) -> None:
        image.set_as_post_processing()

    def _set_processed_status(self, image: DatabaseImage) -> None:
        image.set_as_post_processed()
        self._set_status_if_all_images_post_processed(image.project_uid)

    def _set_failed_status(self, image: DatabaseImage) -> None:
        image.set_as_post_processing_failed()
        self._item_service.select_image(image, False)
        self._set_status_if_all_images_post_processed(image.project_uid)

    def _skip_image(self, image: Image) -> bool:
        return image.status == ImageStatus.POST_PROCESSED

    def _set_status_if_all_images_post_processed(self, project_uid: UUID) -> None:
        project = self._database_service.get_project(project_uid)
        if project.failed:
            return
        any_non_completed = DatabaseImage.get_first_image_for_project(
            project_uid=project.uid,
            exclude_status=[
                ImageStatus.POST_PROCESSING_FAILED,
                ImageStatus.POST_PROCESSED,
            ],
            selected=True,
        )

        if any_non_completed is not None:
            current_app.logger.debug(
                f"Project {project.uid} not yet finished post-processing. "
                f"Image {any_non_completed.uid} has status {any_non_completed.status}."
            )
            return
        current_app.logger.debug(f"Project {project.uid} post-processed.")
        current_app.logger.debug(f"Project {project.uid} status {project.status}.")
        project.set_as_post_processed()


class ImagePreProcessor(ImageProcessor):
    def _set_processing_status(self, image: DatabaseImage) -> None:
        image.set_as_pre_processing()

    def _set_processed_status(self, image: DatabaseImage) -> None:
        image.set_as_pre_processed()
        self._set_status_if_all_images_pre_processed(image.project_uid)

    def _set_failed_status(self, image: DatabaseImage) -> None:
        image.set_as_pre_processing_failed()
        self._item_service.select_image(image, False)
        self._set_status_if_all_images_pre_processed(image.project_uid)

    def _skip_image(self, image: Image) -> bool:
        return image.status == ImageStatus.PRE_PROCESSED

    def _set_status_if_all_images_pre_processed(self, project_uid: UUID) -> None:
        project = self._database_service.get_project(project_uid)
        if project.failed:
            return
        any_non_completed = DatabaseImage.get_first_image_for_project(
            project_uid=project.uid,
            exclude_status=[
                ImageStatus.PRE_PROCESSING_FAILED,
                ImageStatus.PRE_PROCESSED,
            ],
            selected=True,
        )

        if any_non_completed is not None:
            current_app.logger.debug(
                f"Project {project.uid} not yet finished pre-processing. "
                f"Image {any_non_completed.uid} has status {any_non_completed.status}."
            )
            return
        current_app.logger.debug(f"Project {project.uid} pre-processed.")
        current_app.logger.debug(f"Project {project.uid} status {project.status}.")
        project.set_as_pre_processed()
