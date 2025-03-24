import datetime
from typing import Iterable, Optional, Union
from uuid import UUID

from flask import current_app
from slidetap.database import (
    DatabaseBatch,
    NotAllowedActionError,
    db,
)
from slidetap.database.item import DatabaseAnnotation, DatabaseSample
from slidetap.database.project import DatabaseProject
from slidetap.model import Batch, BatchStatus
from slidetap.model.project import Project
from slidetap.model.project_status import ProjectStatus
from slidetap.model.schema.item_schema import ItemSchema
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class BatchService:
    def __init__(
        self,
        validation_service: ValidationService,
        schema_service: SchemaService,
        database_service: DatabaseService,
    ):
        self._validation_service = validation_service
        self._schema_service = schema_service
        self._database_service = database_service

    def create(
        self,
        name: str,
        database_project: Union[UUID, Project, DatabaseProject],
        set_as_default: bool = False,
    ) -> Batch:
        # TODO
        database_project = self._database_service.get_project(database_project)
        batch = Batch(
            UUID(int=0),
            name,
            BatchStatus.INITIALIZED,
            project_uid=database_project.uid,
            created=datetime.datetime.now(),
            is_default=set_as_default,
        )
        database_batch = self._database_service.add_batch(batch)
        database_project.batches.append(database_batch)
        if set_as_default:
            database_project.default_batch_uid = database_batch.uid
        self._handle_project_status(database_project)
        db.session.commit()
        return database_batch.model

    def get(self, uid: UUID) -> Batch:
        return self._database_service.get_batch(uid).model

    def get_all(
        self, project_uid: Optional[UUID] = None, status: Optional[BatchStatus] = None
    ) -> Iterable[Batch]:
        return (
            batch.model
            for batch in self._database_service.get_batches(project_uid, status)
        )

    def update(self, batch: Batch) -> Optional[Batch]:
        existing_batch = self._get(batch.uid)
        if batch is None:
            return None
        existing_batch.name = batch.name
        db.session.commit()
        return existing_batch.model

    def delete(self, uid: UUID) -> Optional[Batch]:
        batch = self._get_optional(uid)
        if batch is None:
            return None
        batch.status = BatchStatus.DELETED
        model = batch.model
        for schema in self._schema_service.items:
            self._delete_or_change_batch_to_default_for_items(
                batch,
                schema,
                default_batch_uid=batch.project.default_batch_uid,
            )
        project = batch.project
        db.session.delete(batch)
        self._handle_project_status(project)
        db.session.commit()
        return model

    def _delete_or_change_batch_to_default_for_items(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        schema: Union[UUID, ItemSchema],
        default_batch_uid: UUID,
        only_non_selected=False,
    ) -> None:
        items = self._database_service.get_items(
            batch=batch, schema=schema, selected=False if only_non_selected else None
        )
        for item in items:
            any_children_in_other_batch = False
            # Observations and images are always removed
            if isinstance(item, DatabaseSample):
                any_children_in_other_batch = any(
                    child.batch_uid != batch
                    for child in item.children + item.images + item.observations
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
                    self._validation_service.validate_item_relations(item)
                db.session.delete(item)
        db.session.commit()

    def _get(self, uid: UUID) -> DatabaseBatch:
        return self._database_service.get_batch(uid)

    def _get_optional(self, uid: UUID) -> Optional[DatabaseBatch]:
        return self._database_service.get_optional_batch(uid)

    def reset(self, batch: Union[UUID, Batch, DatabaseBatch]) -> Batch:
        batch = self._database_service.get_batch(batch)
        if not (
            batch.initialized
            or batch.metadata_searching
            or batch.metadata_search_complete
        ):
            raise NotAllowedActionError("Can only search non-started batches")
        batch = self._database_service.get_batch(batch)
        batch.status = BatchStatus.INITIALIZED
        db.session.commit()
        return batch.model

    def set_as_searching(self, batch: Union[UUID, Batch, DatabaseBatch]) -> Batch:
        batch = self._database_service.get_batch(batch)
        if not batch.initialized:
            error = f"Can only set {BatchStatus.INITIALIZED} batch as {BatchStatus.METADATA_SEARCHING}, was {batch.status}"
            raise NotAllowedActionError(error)
        batch.status = BatchStatus.METADATA_SEARCHING
        current_app.logger.debug(f"batch {batch.uid} set as {batch.status}.")
        db.session.commit()
        return batch.model

    def set_as_search_complete(self, batch: Union[UUID, Batch, DatabaseBatch]) -> Batch:
        batch = self._database_service.get_batch(batch)
        if not batch.metadata_searching:
            error = (
                f"Can only set {BatchStatus.METADATA_SEARCHING} batch as "
                f"{BatchStatus.METADATA_SEARCHING}, was {batch.status}"
            )
            raise NotAllowedActionError(error)

        batch.status = BatchStatus.METADATA_SEARCH_COMPLETE
        current_app.logger.debug(f"Batch {batch.uid} set as {batch.status}.")
        db.session.commit()
        return batch.model

    def set_as_pre_processing(self, batch: Union[UUID, Batch, DatabaseBatch]) -> Batch:
        batch = self._database_service.get_batch(batch)
        if not batch.metadata_search_complete:
            error = (
                f"Can only set {BatchStatus.METADATA_SEARCH_COMPLETE} batch as "
                f"{BatchStatus.IMAGE_PRE_PROCESSING}, was {batch.status}"
            )
            raise NotAllowedActionError(error)
        batch.status = BatchStatus.IMAGE_PRE_PROCESSING
        current_app.logger.debug(f"Batch {batch.uid} set as pre-processing.")
        db.session.commit()
        return batch.model

    def set_as_pre_processed(
        self, batch: Union[UUID, Batch, DatabaseBatch], force: bool = False
    ) -> Batch:
        batch = self._database_service.get_batch(batch)
        if not batch.image_pre_processing and not (
            force and batch.image_post_processing
        ):
            error = (
                f"Can only set {BatchStatus.IMAGE_PRE_PROCESSING} batch as "
                f"{BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE}, was {batch.status}"
            )
            raise NotAllowedActionError(error)
        batch.status = BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        current_app.logger.debug(f"Batch {batch.uid} set as pre-processed.")
        db.session.commit()
        return batch.model

    def set_as_post_processed(
        self, batch: Union[UUID, Batch, DatabaseBatch], force: bool = False
    ) -> Batch:
        batch = self._database_service.get_batch(batch)
        if not batch.image_pre_processing_complete:
            error = (
                f"Can only set {BatchStatus.IMAGE_POST_PROCESSING} batch as "
                f"{BatchStatus.IMAGE_POST_PROCESSING_COMPLETE}, was {batch.status}"
            )
            raise NotAllowedActionError(error)
        batch.status = BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
        current_app.logger.debug(f"Batch {batch.uid} set as post-processd.")
        db.session.commit()
        return batch.model

    def set_as_post_processing(
        self, batch: Union[UUID, Batch, DatabaseBatch], force: bool = False
    ) -> Batch:
        batch = self._database_service.get_batch(batch)
        if not batch.image_pre_processing_complete and not force:
            error = (
                f"Can only set {BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE} batch as "
                f"{BatchStatus.IMAGE_POST_PROCESSING}, was {batch.status}"
            )
            raise NotAllowedActionError(error)
        batch.status = BatchStatus.IMAGE_POST_PROCESSING
        current_app.logger.debug(f"Batch {batch.uid} set as post-processing.")
        return batch.model

    def set_as_completed(self, batch: Union[UUID, Batch, DatabaseBatch]) -> Batch:
        batch = self._database_service.get_batch(batch)
        if not batch.image_post_processing_complete:
            error = (
                f"Can only set {BatchStatus.IMAGE_POST_PROCESSING_COMPLETE} batch as "
                f"{BatchStatus.COMPLETED}, was {batch.status}"
            )
            raise NotAllowedActionError(error)
        batch.status = BatchStatus.COMPLETED
        current_app.logger.debug(f"Batch {batch.uid} set as completed.")
        for item in self._database_service.get_items(batch=batch):
            item.locked = True
            for attribute in item.attributes.values():
                attribute.locked = True
        self._handle_project_status(batch.project)
        db.session.commit()
        return batch.model

    def set_as_failed(self, batch: Union[UUID, Batch, DatabaseBatch]) -> Batch:
        batch = self._database_service.get_batch(batch)
        batch.status = BatchStatus.FAILED
        current_app.logger.debug(f"Batch {batch.uid} set as failed.")
        db.session.commit()
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
