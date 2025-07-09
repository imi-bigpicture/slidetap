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

import datetime
import logging
from typing import Iterable, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseBatch,
    DatabaseProject,
    DatabaseSample,
    NotAllowedActionError,
)
from slidetap.model import Batch, BatchStatus, ItemSchema, ProjectStatus
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class BatchService:
    def __init__(
        self,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
    ):
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service

    def create(
        self,
        batch: Batch,
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            database_project = self._database_service.get_project(
                session,
                batch.project_uid,
            )
            batch.created = datetime.datetime.now()
            database_batch = self._database_service.add_batch(session, batch)
            database_project.batches.add(database_batch)
            if batch.is_default:
                database_project.default_batch_uid = database_batch.uid
            self._handle_project_status(database_project)
            return database_batch.model

    def get(self, uid: UUID, session: Optional[Session] = None) -> Batch:
        with self._database_service.get_session(session) as session:
            return self._database_service.get_batch(session, uid).model

    def get_all(
        self,
        project_uid: Optional[UUID] = None,
        status: Optional[BatchStatus] = None,
        session: Optional[Session] = None,
    ) -> Iterable[Batch]:
        with self._database_service.get_session(session) as session:
            batches = self._database_service.get_batches(session, project_uid, status)
            return [batch.model for batch in batches]

    def update(self, batch: Batch) -> Optional[Batch]:
        with self._database_service.get_session() as session:
            existing_batch = self._database_service.get_optional_batch(
                session,
                batch.uid,
            )
            if existing_batch is None:
                return None
            existing_batch.name = batch.name
            return existing_batch.model

    def delete(self, uid: UUID) -> Optional[Batch]:
        with self._database_service.get_session() as session:
            batch = self._database_service.get_optional_batch(session, uid)
            if batch is None:
                return None
            batch.status = BatchStatus.DELETED
            model = batch.model
            assert batch.project.default_batch_uid is not None
            for schema in self._schema_service.items.values():
                self._delete_or_change_batch_to_default_for_items(
                    batch,
                    schema,
                    default_batch_uid=batch.project.default_batch_uid,
                    session=session,
                )
            project = batch.project
            session.delete(batch)
            self._handle_project_status(project)
            session.commit()
            return model

    def _delete_or_change_batch_to_default_for_items(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        schema: ItemSchema,
        default_batch_uid: UUID,
        session: Session,
        only_non_selected=False,
    ) -> None:

        items = self._database_service.get_items(
            batch=batch,
            schema=schema,
            selected=False if only_non_selected else None,
            session=session,
        )
        for item in items:
            any_children_in_other_batch = False
            # Observations and images are always removed
            if isinstance(item, DatabaseSample):
                any_children_in_other_batch = any(
                    child.batch_uid != batch
                    for child in item.children | item.images | item.observations
                )
            elif isinstance(item, DatabaseAnnotation):
                any_children_in_other_batch = any(
                    child.batch_uid != batch for child in item.observations
                )
            if any_children_in_other_batch:
                item.batch_uid = default_batch_uid
            else:
                if item.selected:
                    # If the item is selected and related to items in other batches,
                    # the relations needs to be re-valuated
                    item.selected = False
                    self._validation_service.validate_item_relations(item, session)
                session.delete(item)
        session.commit()

    def reset(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not (
                batch.initialized
                or batch.metadata_searching
                or batch.metadata_search_complete
            ):
                raise NotAllowedActionError("Can only search non-started batches")
            batch.status = BatchStatus.INITIALIZED
            session.commit()
            return batch.model

    def set_as_searching(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.initialized:
                error = f"Can only set {BatchStatus.INITIALIZED} batch as {BatchStatus.METADATA_SEARCHING}, was {batch.status}"
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.METADATA_SEARCHING
            logging.info(f"Batch {batch.uid} set as {batch.status}.")
            session.commit()
            return batch.model

    def set_as_search_complete(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.metadata_searching:
                error = (
                    f"Can only set {BatchStatus.METADATA_SEARCHING} batch as "
                    f"{BatchStatus.METADATA_SEARCH_COMPLETE}, was {batch.status}"
                )
                raise NotAllowedActionError(error)

            batch.status = BatchStatus.METADATA_SEARCH_COMPLETE
            logging.info(f"Batch {batch.uid} set as {batch.status}.")
            session.commit()
            return batch.model

    def set_as_pre_processing(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.metadata_search_complete:
                error = (
                    f"Can only set {BatchStatus.METADATA_SEARCH_COMPLETE} batch as "
                    f"{BatchStatus.IMAGE_PRE_PROCESSING}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.IMAGE_PRE_PROCESSING
            logging.info(f"Batch {batch.uid} set as pre-processing.")
            session.commit()
            return batch.model

    def set_as_pre_processed(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        force: bool = False,
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.image_pre_processing and not (
                force and batch.image_post_processing
            ):
                error = (
                    f"Can only set {BatchStatus.IMAGE_PRE_PROCESSING} batch as "
                    f"{BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
            logging.info(f"Batch {batch.uid} set as pre-processed.")
            session.commit()
            return batch.model

    def set_as_post_processed(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        force: bool = False,
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.image_post_processing:
                error = (
                    f"Can only set {BatchStatus.IMAGE_POST_PROCESSING} batch as "
                    f"{BatchStatus.IMAGE_POST_PROCESSING_COMPLETE}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
            logging.info(f"Batch {batch.uid} set as post-processd.")
            session.commit()
            return batch.model

    def set_as_post_processing(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        force: bool = False,
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.image_pre_processing_complete and not force:
                error = (
                    f"Can only set {BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE} batch as "
                    f"{BatchStatus.IMAGE_POST_PROCESSING}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.IMAGE_POST_PROCESSING
            logging.info(f"Batch {batch.uid} set as post-processing.")
            return batch.model

    def set_as_completed(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.image_post_processing_complete:
                error = (
                    f"Can only set {BatchStatus.IMAGE_POST_PROCESSING_COMPLETE} batch as "
                    f"{BatchStatus.COMPLETED}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.COMPLETED
            logging.info(f"Batch {batch.uid} set as completed.")
            items = (
                item
                for schema in self._schema_service.items.values()
                for item in self._database_service.get_items(
                    session=session, schema=schema, batch=batch
                )
            )
            for item in items:
                item.locked = True
                for attribute in item.attributes:
                    attribute.locked = True
            self._handle_project_status(batch.project)
            session.commit()
            return batch.model

    def set_as_failed(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        session: Optional[Session] = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            batch.status = BatchStatus.FAILED
            logging.info(f"Batch {batch.uid} set as failed.")
            session.commit()
            return batch.model

    def _handle_project_status(self, project: DatabaseProject):
        batches = project.batches
        any_all_completed_batch_in_project = all(
            batch.status == BatchStatus.COMPLETED for batch in batches
        )
        if (
            any_all_completed_batch_in_project
            and project.status != ProjectStatus.COMPLETED
        ):
            project.status = ProjectStatus.COMPLETED
        elif project.status == ProjectStatus.COMPLETED:
            project.status = ProjectStatus.IN_PROGRESS
