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
from typing import Optional
from uuid import UUID

from slidetap.model import Batch, Image, RootSchema
from slidetap.services import BatchService, DatabaseService, SchemaService
from slidetap.task import Scheduler


class ImageExportService:
    def __init__(
        self,
        scheduler: Scheduler,
        batch_service: BatchService,
        schema_service: SchemaService,
        database_service: DatabaseService,
        root_schema: RootSchema,
    ):
        self._scheduler = scheduler
        self._batch_service = batch_service
        self._schema_service = schema_service
        self._database_service = database_service
        self._image_schemas = root_schema.images.values()

    def re_export(self, batch: Batch, image: Image):
        """Should re-export the image to storage."""
        self._scheduler.post_process_image(image)

    def export(
        self,
        batch_uid: UUID,
    ) -> Optional[Batch]:
        """Process a batch."""
        with self._database_service.get_session() as session:
            database_batch = self._database_service.get_batch(session, batch_uid)
            for item_schema in self._schema_service.items:
                self._database_service.delete_items(
                    session, batch_uid, item_schema, only_non_selected=True
                )
            batch = self._batch_service.set_as_post_processing(
                database_batch, False, session
            )
        for image_schema in self._image_schemas:
            logging.info(
                f"Post processing images of schema {image_schema} for batch {batch.uid}."
            )
            self._scheduler.post_process_images_in_batch(batch, image_schema)
        return batch
