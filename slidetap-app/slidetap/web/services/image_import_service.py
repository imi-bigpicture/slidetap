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
from typing import Sequence

from slidetap.model import Batch, Image, ImageSchema
from slidetap.service_provider import RootSchema
from slidetap.services import DatabaseService
from slidetap.task import Scheduler


class ImageImportService:
    def __init__(
        self,
        scheduler: Scheduler,
        database_service: DatabaseService,
        root_schema: RootSchema,
    ):
        self._scheduler = scheduler
        self._database_service = database_service
        self._image_schemas = root_schema.images.values()

    def pre_process_batch(self, batch: Batch):
        for image_schema in self._image_schemas:
            logging.info(
                f"Pre-processing images for batch {batch.uid} and schema {image_schema.uid}."
            )
            self._scheduler.pre_process_images_in_batch(batch, image_schema)

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
