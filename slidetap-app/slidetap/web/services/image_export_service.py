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


import logging
from typing import Sequence

from slidetap.model import Batch, Image
from slidetap.model.schema.item_schema import ImageSchema
from slidetap.service_provider import RootSchema
from slidetap.services import DatabaseService
from slidetap.task import Scheduler


class ImageExportService:
    def __init__(
        self,
        scheduler: Scheduler,
        database_service: DatabaseService,
        root_schema: RootSchema,
    ):
        self._scheduler = scheduler
        self._database_service = database_service
        self._image_schemas = root_schema.images.values()

    def export(self, batch: Batch):
        """Should export the image to storage."""
        for image_schema in self._image_schemas:
            logging.info(
                f"Post processing images of schema {image_schema} for batch {batch.uid}."
            )
            self._scheduler.post_process_images_in_batch(batch, image_schema)

    def re_export(self, batch: Batch, image: Image):
        """Should re-export the image to storage."""
        self._scheduler.post_process_image(image)
