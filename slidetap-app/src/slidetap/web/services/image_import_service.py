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
from typing import Optional
from uuid import UUID

from slidetap.model import Batch, Image, RootSchema
from slidetap.services import BatchService, DatabaseService, SchemaService
from slidetap.task import Scheduler


class ImageImportService:
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

    def pre_process_batch(
        self,
        batch_uid: UUID,
    ) -> Optional[Batch]:
        """Pre-process a batch."""
        with self._database_service.get_session() as session:
            database_batch = self._database_service.get_optional_batch(
                session, batch_uid
            )
            if database_batch is None:
                return None
            for item_schema in self._schema_service.items.values():
                self._database_service.delete_items(
                    session, item_schema, batch_uid, only_non_selected=True
                )
            batch = self._batch_service.set_as_pre_processing(database_batch, session)
            session.commit()
        for image_schema in self._image_schemas:
            logging.info(
                f"Pre-processing images for batch {batch.uid} and schema {image_schema.uid}."
            )
            self._scheduler.pre_process_images_in_batch(batch, image_schema)
        return batch
