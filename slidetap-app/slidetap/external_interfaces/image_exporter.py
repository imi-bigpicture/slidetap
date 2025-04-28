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

from slidetap.model import Batch, Image
from slidetap.model.schema.item_schema import ImageSchema
from slidetap.services import DatabaseService
from slidetap.task import Scheduler


class ImageExporter:
    @abstractmethod
    def export(self, batch: Batch):
        """Should export the images for a project."""
        raise NotImplementedError()

    @abstractmethod
    def re_export(self, batch: Batch, image: Image):
        """Should re-export the image to storage."""
        raise NotImplementedError()


class BackgroundImageExporter(ImageExporter):
    def __init__(
        self,
        scheduler: Scheduler,
        database_service: DatabaseService,
        image_schema: ImageSchema,
    ):
        self._scheduler = scheduler
        self._database_service = database_service
        self._image_schema = image_schema

    def export(self, batch: Batch):
        """Should export the image to storage."""
        self._scheduler.post_process_images_in_batch(batch, self._image_schema)

    def re_export(self, batch: Batch, image: Image):
        """Should re-export the image to storage."""
        self._scheduler.post_process_image(image)
