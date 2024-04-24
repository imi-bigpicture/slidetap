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

from slidetap.database import Image, Project
from slidetap.importer.importer import Importer
from slidetap.model import Session


class ImageImporter(Importer, metaclass=ABCMeta):
    """Metaclass for image importer."""

    @abstractmethod
    def pre_process(self, session: Session, project: Project):
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
    def redo_image_download(self, session: Session, image: Image):
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
