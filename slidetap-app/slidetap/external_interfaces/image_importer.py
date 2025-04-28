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

import logging
from abc import ABCMeta, abstractmethod
from typing import Optional

from flask import Blueprint

from slidetap.model import Batch, Image, ImageSchema
from slidetap.services import DatabaseService
from slidetap.task import Scheduler


class ImageImporter(metaclass=ABCMeta):
    """Metaclass for image importer."""

    @property
    def blueprint(self) -> Optional[Blueprint]:
        """If importer have api endpoints they should be register
        to a blueprint and returned using this property."""
        return None

    def reset_batch(self, batch: Batch):
        """Should reset any internally stored data for project."""
        pass

    @abstractmethod
    def pre_process_batch(self, batch: Batch):
        """Should pre-process images matching images defined in project.

        Parameters
        ----------
        project: Project
            Project to pre-process.

        """
        raise NotImplementedError()

    @abstractmethod
    def redo_image_download(self, image: Image):
        """Should redo download for a single image.

        Parameters
        ----------
        image: Image
            Image to pre-process.

        """
        raise NotImplementedError()

    @abstractmethod
    def redo_image_pre_processing(self, image: Image):
        """Should redo pre-processing for a single image.

        Parameters
        ----------
        image: Image
            Image to pre-process.

        """
        raise NotImplementedError()


class BackgroundImageImporter(ImageImporter):
    def __init__(
        self,
        scheduler: Scheduler,
        database_service: DatabaseService,
        image_schema: ImageSchema,
    ):
        self._scheduler = scheduler
        self._database_service = database_service
        self._image_schema = image_schema

    def pre_process_batch(self, batch: Batch):
        logging.info(f"Pre-processing images for batch {batch.uid}")
        self._scheduler.pre_process_images_in_batch(batch, self._image_schema)

    def redo_image_download(self, image: Image):
        with self._database_service.get_session() as database_session:
            database_image = self._database_service.get_image(database_session, image)
            database_image.reset_as_not_started()
        self._scheduler.download_image(image)

    def redo_image_pre_processing(self, image: Image):
        with self._database_service.get_session() as database_session:
            database_image = self._database_service.get_image(database_session, image)
            database_image.reset_as_downloaded()
        self._scheduler.pre_process_image(image)


class PreLoadedImageImporter(BackgroundImageImporter):
    """Image importer that just runs the pre-processor on all loaded images."""

    def pre_process_batch(self, batch: Batch):
        with self._database_service.get_session() as database_session:
            for image in self._database_service.get_images(
                database_session, batch=batch
            ):
                image.set_as_downloading()
                image.set_as_downloaded()
                self._scheduler.pre_process_image(image.model)

    def redo_image_pre_processing(self, image: Image):
        with self._database_service.get_session() as database_session:
            database_image = self._database_service.get_image(database_session, image)
            database_image.set_as_downloading()
            database_image.set_as_downloaded()
        self._scheduler.pre_process_image(image)

    def redo_image_download(self, image: Image):
        with self._database_service.get_session() as database_session:
            database_image = self._database_service.get_image(database_session, image)
            database_image.set_as_downloading()
            database_image.set_as_downloaded()
