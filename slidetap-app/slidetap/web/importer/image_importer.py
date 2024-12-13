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
from typing import Optional
from uuid import UUID

from flask import Flask, current_app

from slidetap.database import DatabaseImage
from slidetap.model import UserSession
from slidetap.model.item import Image
from slidetap.model.project import Project
from slidetap.model.schema.root_schema import RootSchema
from slidetap.task.scheduler import Scheduler
from slidetap.web.importer.importer import Importer


class ImageImporter(Importer, metaclass=ABCMeta):
    """Metaclass for image importer."""

    @abstractmethod
    def pre_process(self, session: UserSession, project: Project):
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
    def __init__(
        self,
        schema: RootSchema,
        scheduler: Scheduler,
        app: Optional[Flask] = None,
    ):
        super().__init__(schema, scheduler, app)

    def pre_process(self, session: UserSession, project_uid: UUID):
        current_app.logger.info(f"Pre-processing images for project {project_uid}")
        for image in self._database_service.get_project_images(project_uid):
            current_app.logger.info(f"Pre-processing image {image.uid}")
            self._scheduler.download_and_pre_process_image(image.uid)

    def redo_image_download(self, session: UserSession, image_uid: UUID):
        database_image = self._database_service.get_image(image_uid)
        database_image.reset_as_not_started()
        self._scheduler.download_image(image_uid)

    def redo_image_pre_processing(self, image: Image):
        database_image = self._database_service.get_image(image.uid)
        database_image.reset_as_downloaded()
        self._scheduler.pre_process_image(image.uid)


class PreLoadedImageImporter(BackgroundImageImporter):
    """Image importer that just runs the pre-processor on all loaded images."""

    def pre_process(self, session: UserSession, project_uid: UUID):
        for image in self._database_service.get_project_images(project_uid):
            self._scheduler.pre_process_image(image.uid)

    def redo_image_pre_processing(self, image: DatabaseImage):
        pass

    def redo_image_download(self, session: UserSession, image_uid: UUID):
        self._scheduler.pre_process_image(image_uid)
