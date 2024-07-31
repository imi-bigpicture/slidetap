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

from flask import Flask, current_app

from slidetap.database import Image, Project
from slidetap.database.schema.item_schema import ImageSchema
from slidetap.importer.importer import Importer
from slidetap.model import UserSession
from slidetap.tasks.scheduler import Scheduler


class ImageImporter(Importer, metaclass=ABCMeta):
    """Metaclass for image importer."""

    def __init__(
        self,
        scheduler: Scheduler,
        app: Optional[Flask] = None,
    ):
        super().__init__(scheduler, app)

    def init_app(self, app: Flask):
        super().init_app(app)

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


class SchedulingImageImporter(ImageImporter):
    def __init__(
        self,
        scheduler: Scheduler,
        image_schema_name: str,
        app: Optional[Flask] = None,
    ):
        self._image_schema_name = image_schema_name
        super().__init__(scheduler, app)

    def pre_process(self, session: UserSession, project: Project):
        current_app.logger.info(f"Pre-processing images for project {project.uid}")
        for image in self._get_images_in_project(project):
            current_app.logger.info(f"Pre-processing image {image.uid}")
            self._scheduler.download_and_pre_process_image(image)

    def redo_image_download(self, session: UserSession, image: Image):
        image.reset_as_not_started()
        self._scheduler.download_image(image)

    def redo_image_pre_processing(self, image: Image):
        image.reset_as_downloaded()
        self._scheduler.pre_process_image(image)

    def _get_images_in_project(self, project: Project):
        image_schema = ImageSchema.get(project.root_schema, self._image_schema_name)
        return Image.get_for_project(project.uid, image_schema.uid, selected=True)


class PreLoadedImageImporter(SchedulingImageImporter):
    """Image importer that just runs the pre-processor on all loaded images."""

    def pre_process(self, session: UserSession, project: Project):
        for image in self._get_images_in_project(project):
            self._scheduler.pre_process_image(image)

    def redo_image_pre_processing(self, image: Image):
        pass

    def redo_image_download(self, session: UserSession, image: Image):
        self.pre_process(session, image.project)
