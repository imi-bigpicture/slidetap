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
from typing import List, Optional
from uuid import UUID

from flask import current_app
from werkzeug.datastructures import FileStorage

from slidetap.exporter import ImageExporter, MetadataExporter
from slidetap.importer import ImageImporter, MetadataImporter
from slidetap.model import ImageStatus, Project, UserSession
from slidetap.model.batch import Batch
from slidetap.services.batch_service import BatchService
from slidetap.services.database_service import DatabaseService
from slidetap.services.dataset_service import DatasetService
from slidetap.services.project_service import ProjectService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class ProcessingService:
    def __init__(
        self,
        image_importer: ImageImporter,
        image_exporter: ImageExporter,
        metadata_importer: MetadataImporter,
        metadata_exporter: MetadataExporter,
        project_service: ProjectService,
        dataset_service: DatasetService,
        batch_service: BatchService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
    ) -> None:
        self._image_importer = image_importer
        self._image_exporter = image_exporter
        self._metadata_importer = metadata_importer
        self._metadata_exporter = metadata_exporter
        self._project_service = project_service
        self._dataset_service = dataset_service
        self._batch_service = batch_service
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service

    def retry_image(self, user_session: UserSession, image_uid: UUID) -> None:
        with self._database_service.get_session() as session:
            image = self._database_service.get_image(session, image_uid)
            if image is None:
                raise ValueError(f"Image {image_uid} does not exist.")
            if image.batch is None:
                raise ValueError(f"Image {image_uid} does not belong to a batch.")
            image.status_message = ""
            if image.status == ImageStatus.DOWNLOADING_FAILED:
                image.reset_as_not_started()
                self._image_importer.redo_image_download(user_session, image.model)
            elif image.status == ImageStatus.PRE_PROCESSING_FAILED:
                image.reset_as_downloaded()
                self._image_importer.redo_image_pre_processing(image.model)
            elif image.status == ImageStatus.POST_PROCESSING_FAILED:
                image.reset_as_pre_processed()
                self._image_exporter.re_export(image.batch.model, image.model)

    def create_project(self, user_session: UserSession, project_name: str) -> Project:
        with self._database_service.get_session() as session:
            dataset = self._metadata_importer.create_dataset(user_session, project_name)
            dataset = self._dataset_service.create(dataset, session=session)
            project = self._metadata_importer.create_project(
                user_session, project_name, dataset.uid
            )
            project = self._project_service.create(project, session=session)
            self._batch_service.create("Default", project.uid, True, session=session)
            return project

    def start_metadata_search(
        self, batch_uid: UUID, user_session: UserSession, file: FileStorage
    ) -> Optional[Batch]:
        with self._database_service.get_session() as session:
            database_batch = self._database_service.get_batch(
                session,
                batch_uid,
            )
            self._batch_service.reset(database_batch, session)
            self._metadata_importer.reset_batch(database_batch.model)
            self._image_importer.reset_batch(database_batch.model)
            for item_schema in self._schema_service.items:
                self._database_service.delete_items(
                    session,
                    batch_uid,
                    item_schema,
                )
            batch = self._batch_service.set_as_searching(database_batch, session)
            dataset = database_batch.project.dataset.model
            session.commit()

        self._metadata_importer.search(user_session, dataset, batch, file)
        return batch

    def pre_process_batch(
        self, batch_uid: UUID, user_session: UserSession
    ) -> Optional[Batch]:
        with self._database_service.get_session() as session:
            database_batch = self._database_service.get_optional_batch(
                session, batch_uid
            )
            if database_batch is None:
                return None
            for item_schema in self._schema_service.items:
                self._database_service.delete_items(
                    session, batch_uid, item_schema, only_non_selected=True
                )
            batch = self._batch_service.set_as_pre_processing(database_batch, session)
            session.commit()
        self._image_importer.pre_process_batch(user_session, batch)
        return batch

    def process_batch(
        self, batch_uid: UUID, user_session: UserSession
    ) -> Optional[Batch]:
        with self._database_service.get_session() as session:

            database_batch = self._database_service.get_batch(session, batch_uid)
            for item_schema in self._schema_service.items:
                self._database_service.delete_items(
                    session, batch_uid, item_schema, only_non_selected=True
                )
            batch = self._batch_service.set_as_post_processing(
                database_batch, False, session
            )
        self._image_exporter.export(batch)
        return batch

    def export_project(self, project_uid: UUID) -> Project:
        with self._database_service.get_session() as session:
            database_project = self._database_service.get_project(session, project_uid)
            if not database_project.completed:
                raise ValueError("Can only export a completed project.")
            for batch in database_project.batches:
                if not batch.completed:
                    raise ValueError("Can only export completed batches.")
            if not database_project.valid:
                raise ValueError("Can only export a valid project.")
            logging.info("Exporting project to outbox")
            project = database_project.model
        self._metadata_exporter.export(project)
        return database_project.model

    def restore_project(self, project_uid: UUID) -> Project:
        with self._database_service.get_session() as session:
            database_project = self._database_service.get_project(session, project_uid)
            project = database_project.model
            batches: List[Batch] = []
            for database_batch in database_project.batches:
                if database_batch.image_post_processing:
                    logging.info(
                        f"Restoring batch {database_batch.uid} to pre-processed."
                    )
                    batch = self._batch_service.set_as_pre_processed(
                        database_batch, True, session
                    )
                    # TODO move this to image exporter
                    images = self._database_service.get_images(
                        session, batch=database_batch
                    )
                    for image in [image for image in images if image.post_processing]:
                        logging.debug(f"Restoring image {image.uid} to pre-processed.")
                        image.set_as_pre_processed(True)
                    logging.info(f"Restarting export of project {project_uid}.")
                    batches.append(batch)

        for batch in batches:
            self._image_exporter.export(batch)
        return project

    def restore_all_projects(self) -> None:
        for project in self._project_service.get_all():
            self.restore_project(project.uid)
