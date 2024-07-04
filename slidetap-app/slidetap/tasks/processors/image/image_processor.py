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
from typing import Optional
from uuid import UUID

from flask import Flask

from slidetap.database import Image
from slidetap.flask_extension import FlaskExtension
from slidetap.storage import Storage


class ImageProcessor(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for an image exporter that runs jobs in background threads."""

    def __init__(
        self,
        storage: Storage,
        app: Optional[Flask] = None,
    ):
        self._storage = storage
        super().__init__(app)

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

    @abstractmethod
    def run(self, image_uid: UUID):
        """The action that should be run for a job.

        Parameters
        ----------
        image_uid: UUID
            Identifier for the image to process.

        """
        raise NotImplementedError()
