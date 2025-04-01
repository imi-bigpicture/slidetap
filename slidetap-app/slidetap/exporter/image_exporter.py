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


from abc import abstractmethod

from slidetap.exporter.exporter import Exporter
from slidetap.model.batch import Batch
from slidetap.model.item import Image


class ImageExporter(Exporter):
    @abstractmethod
    def export(self, project: Batch):
        """Should export the images for a project."""
        raise NotImplementedError()

    @abstractmethod
    def re_export(self, batch: Batch, image: Image):
        """Should re-export the image to storage."""
        raise NotImplementedError()


class BackgroundImageExporter(ImageExporter):
    def export(self, batch: Batch):
        """Should export the image to storage."""
        with self._database_service.get_session() as session:
            images = self._database_service.get_images(session, batch=batch)
            for image in images:
                self._scheduler.post_process_image(image.model)

    def re_export(self, batch: Batch, image: Image):
        """Should re-export the image to storage."""
        self._scheduler.post_process_image(image)
