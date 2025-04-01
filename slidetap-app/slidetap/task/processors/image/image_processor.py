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
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Iterable, Optional
from uuid import UUID

from slidetap.config import Config
from slidetap.database import DatabaseImage, DatabaseImageFile
from slidetap.database.project import DatabaseBatch
from slidetap.model import ImageStatus
from slidetap.model.item import Image
from slidetap.model.schema.root_schema import RootSchema
from slidetap.storage import Storage
from slidetap.task.processors.image.image_processing_step import (
    ImageProcessingStep,
)
from slidetap.task.processors.processor import Processor
from sqlalchemy.orm import Session


class ImageProcessor(Processor, metaclass=ABCMeta):
    """Image processor that runs a sequence of steps on the processing image."""

    def __init__(
        self,
        root_schema: RootSchema,
        storage: Storage,
        config: Config,
        steps: Optional[Iterable[ImageProcessingStep]] = None,
    ):
        """Create a StepImageProcessor.

        Parameters
        ----------
        storage: Storage
        steps: Iterable[ImageProcessingStep]
        """
        if steps is None:
            steps = []
        self._steps = steps
        self._storage = storage
        super().__init__(root_schema, config)

    def run(self, image_uid: UUID):
        with self._database_service.get_session() as session:
            database_image = self._database_service.get_image(session, image_uid)
            database_batch = self._database_service.get_batch(
                session, database_image.batch_uid
            )
            project = self._database_service.get_project(
                session, database_batch.project_uid
            ).model
            image = database_image.model
            logging.debug(f"Processing image {image.uid}.")
            if self._skip_image(image):
                logging.debug(f"Skipping image {image.uid} as it is already processed.")
                return
            if image.folder_path is None:
                self._set_failed_status(session, database_image)
                session.commit()
                logging.error(f"Image {image.uid} does not have a folder path.")
                return
            self._set_processing_status(database_image)
            processing_path = Path(image.folder_path)
            try:
                for step in self._steps:
                    try:
                        processing_path, image = step.run(
                            self._root_schema,
                            self._storage,
                            project,
                            image,
                            processing_path,
                        )
                    except Exception as exception:
                        session.rollback()
                        logging.error(
                            f"Processing failed for {image.uid} name {image.name} "
                            f"at step {step}.",
                            exc_info=True,
                        )
                        database_image.status_message = (
                            f"Failed during processing at step {step} due to "
                            f"exception {exception}."
                        )
                        self._set_failed_status(session, database_image)

                        session.commit()
                        return
                logging.debug(f"Processing complete for {image.uid}.")
                database_image.folder_path = str(processing_path)
                database_image.files = [
                    DatabaseImageFile(file.filename) for file in image.files
                ]
                if image.thumbnail_path is not None:
                    database_image.thumbnail_path = image.thumbnail_path
                self._attribute_service.update_for_item(
                    database_image, image.attributes, session=session
                )
                self._set_processed_status(session, database_image)

                session.commit()
            finally:
                logging.debug(f"Cleanup {image.uid} name {image.name}.")
                for step in self._steps:
                    step.cleanup(project, image)

    @abstractmethod
    def _set_failed_status(self, session: Session, image: DatabaseImage) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _set_processing_status(self, image: DatabaseImage) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _set_processed_status(self, session: Session, image: DatabaseImage) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _skip_image(self, image: Image) -> bool:
        raise NotImplementedError()


class ImagePostProcessor(ImageProcessor):
    def _set_processing_status(self, image: DatabaseImage) -> None:
        image.set_as_post_processing()

    def _set_processed_status(self, session: Session, image: DatabaseImage) -> None:
        image.set_as_post_processed()
        session.commit()
        self._set_status_if_all_images_post_processed(session, image.batch)

    def _set_failed_status(self, session: Session, image: DatabaseImage) -> None:
        image.set_as_post_processing_failed()
        self._item_service.select_image(image, False, session=session)
        session.commit()
        self._set_status_if_all_images_post_processed(session, image.batch)

    def _skip_image(self, image: Image) -> bool:
        return image.status == ImageStatus.POST_PROCESSED

    def _set_status_if_all_images_post_processed(
        self, session: Session, batch: Optional[DatabaseBatch]
    ) -> None:
        if batch is None or batch.failed:
            return
        any_non_completed = self._database_service.get_first_image_for_batch(
            session,
            batch_uid=batch.uid,
            exclude_status=[
                ImageStatus.POST_PROCESSING_FAILED,
                ImageStatus.POST_PROCESSED,
            ],
            selected=True,
        )

        if any_non_completed is not None:
            logging.debug(
                f"Batch {batch.uid} not yet finished post-processing. "
                f"Image {any_non_completed.uid} has status {any_non_completed.status}."
            )
            return
        logging.debug(f"Batch {batch.uid} post-processed.")
        logging.debug(f"Batch {batch.uid} status {batch.status}.")
        self._batch_service.set_as_post_processed(batch, session=session)


class ImagePreProcessor(ImageProcessor):
    def _set_processing_status(self, image: DatabaseImage) -> None:
        image.set_as_pre_processing()

    def _set_processed_status(self, session: Session, image: DatabaseImage) -> None:
        image.set_as_pre_processed()
        session.commit()
        self._set_status_if_all_images_pre_processed(session, image.batch)

    def _set_failed_status(self, session: Session, image: DatabaseImage) -> None:
        image.set_as_pre_processing_failed()
        self._item_service.select_image(image, False, session=session)
        session.commit()
        self._set_status_if_all_images_pre_processed(session, image.batch)

    def _skip_image(self, image: Image) -> bool:
        return image.status == ImageStatus.PRE_PROCESSED

    def _set_status_if_all_images_pre_processed(
        self, session: Session, batch: Optional[DatabaseBatch]
    ) -> None:
        if batch is None or batch.failed:
            return
        any_non_completed = self._database_service.get_first_image_for_batch(
            session,
            batch_uid=batch.uid,
            exclude_status=[
                ImageStatus.PRE_PROCESSING_FAILED,
                ImageStatus.PRE_PROCESSED,
            ],
            selected=True,
        )

        if any_non_completed is not None:
            logging.debug(
                f"Batch {batch.uid} not yet finished pre-processing. "
                f"Image {any_non_completed.uid} has status {any_non_completed.status}."
            )
            return
        logging.debug(f"Batch {batch.uid} pre-processed.")
        logging.debug(f"Batch {batch.uid} status {batch.status}.")
        self._batch_service.set_as_pre_processed(batch, session=session)
