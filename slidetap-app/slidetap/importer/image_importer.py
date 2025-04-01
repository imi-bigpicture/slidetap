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

from abc import ABCMeta, abstractmethod
import logging

from flask import current_app

from slidetap.config import Config
from slidetap.importer.importer import Importer
from slidetap.model import UserSession
from slidetap.model.batch import Batch
from slidetap.model.item import Image
from slidetap.model.schema.root_schema import RootSchema
from slidetap.task.scheduler import Scheduler


class ImageImporter(Importer, metaclass=ABCMeta):
    """Metaclass for image importer."""

    @abstractmethod
    def pre_process_batch(self, session: UserSession, batch: Batch):
        """Should pre-process images matching images defined in project.

        Parameters
        ----------
        session: Session
            User session for request.
        project: Project
            Project to pre-process.

        """
        raise NotImplementedError()

    @abstractmethod
    def redo_image_download(self, session: UserSession, image: Image):
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
    def __init__(self, schema: RootSchema, scheduler: Scheduler, config: Config):
        super().__init__(schema, scheduler, config)

    def pre_process_batch(self, session: UserSession, batch: Batch):
        logging.info(f"Pre-processing images for batch {batch.uid}")
        with self._database_service.get_session() as database_session:
            for image in self._database_service.get_images(
                database_session, batch=batch
            ):
                logging.info(f"Pre-processing image {image.uid}")
                self._scheduler.download_and_pre_process_image(image.model)

    def redo_image_download(self, session: UserSession, image: Image):
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

    def pre_process_batch(self, session: UserSession, batch: Batch):
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

    def redo_image_download(self, session: UserSession, image: Image):
        with self._database_service.get_session() as database_session:
            database_image = self._database_service.get_image(database_session, image)
            database_image.set_as_downloading()
            database_image.set_as_downloaded()
