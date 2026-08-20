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
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseBatch,
    DatabaseImage,
    DatabaseItem,
    DatabaseProject,
    NotAllowedActionError,
)
from slidetap.model import (
    Batch,
    BatchCreate,
    BatchStatus,
    ImageStatus,
    ItemSchema,
    ProjectStatus,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.review_service import ReviewService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class BatchService:
    def __init__(
        self,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
        review_service: ReviewService,
    ):
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service
        self._review_service = review_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def create(
        self,
        batch: BatchCreate,
        session: Session | None = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            database_project = self._database_service.get_project(
                session,
                batch.project_uid,
            )
            database_batch = self._database_service.add_batch(session, batch)
            database_project.batches.add(database_batch)
            if batch.is_default:
                database_project.default_batch_uid = database_batch.uid
            self._handle_project_status(database_project)
            return database_batch.model

    def get(self, uid: UUID, session: Session | None = None) -> Batch:
        with self._database_service.get_session(session) as session:
            return self._database_service.get_batch(session, uid).model

    def get_optional(self, uid: UUID, session: Session | None = None) -> Batch | None:
        with self._database_service.get_session(session) as session:
            database_batch = self._database_service.get_optional_batch(session, uid)
            return database_batch.model if database_batch is not None else None

    def get_all(
        self,
        project_uid: UUID | None = None,
        status: BatchStatus | None = None,
        session: Session | None = None,
    ) -> Iterable[Batch]:
        with self._database_service.get_session(session) as session:
            batches = self._database_service.get_batches(
                session, project_uid, status, load_relations=True
            )
            return [batch.model for batch in batches]

    def update(self, batch: Batch) -> Batch | None:
        with self._database_service.get_session() as session:
            existing_batch = self._database_service.get_optional_batch(
                session,
                batch.uid,
            )
            if existing_batch is None:
                return None
            existing_batch.name = batch.name
            return existing_batch.model

    def delete(self, uid: UUID) -> Batch | None:
        with self._database_service.get_session() as session:
            batch = self._database_service.get_optional_batch(session, uid)
            if batch is None:
                return None
            batch.status = BatchStatus.DELETED
            model = batch.model
            if batch.project.default_batch_uid is None:
                raise ValueError("Project does not have a default batch uid.")
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

    def move_shared_items_to_other_batch(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
    ) -> int:
        """Hand items another batch hangs off over to that batch.

        Before a batch is searched again, what its last search left is cleared
        out. An item of it can have been picked up by a later batch, though:
        the being a case created is the same being for a case found in the next
        batch, and it is stored once. Deleting it would take that later batch's
        case with it, and the later batch has no reason to be searched again.

        It is handed to a batch that still hangs off it instead. The search
        that follows finds it again by identifier and hangs its new items off
        it, so the item keeps whatever a curator did to it, and the batch it
        moved to keeps working either way.

        Returns
        -------
        int
            How many items were handed over.
        """
        with self._database_service.get_session(session) as session:
            batch_uid = self._database_service.get_batch(session, batch).uid
            moved = 0
            for schema in self._schema_service.items.values():
                items = list(
                    self._database_service.get_items(
                        batch=batch_uid,
                        schema=schema,
                        session=session,
                    )
                )
                for item in items:
                    holders = self._held_by_other_batches(item, batch_uid)
                    if not holders:
                        continue
                    item.batch_uid = self._batch_to_hand_over_to(session, holders)
                    moved += 1
            session.commit()
            if moved:
                self._logger.info(
                    f"Handed {moved} item(s) of batch {batch_uid} over to the "
                    "batches hanging off them."
                )
            return moved

    def _held_by_other_batches(
        self,
        item: DatabaseItem,
        batch_uid: UUID,
    ) -> set[DatabaseItem]:
        """What hangs directly under ``item`` from outside ``batch_uid``.

        An item something outside the batch hangs off is not the batch's alone
        to delete: a specimen without its being, or an image without its slide,
        is not something the batch it sits in can be left with.
        """
        return {
            child
            for child in self._database_service.get_children(item)
            if child.batch_uid != batch_uid
        }

    def _batch_to_hand_over_to(
        self,
        session: Session,
        holders: set[DatabaseItem],
    ) -> UUID:
        """Which batch an item held from outside is handed to.

        The earliest of the batches hanging off it. Which one is arbitrary when
        several do -- the item is shared either way -- so the oldest is taken to
        keep the choice the same from one run to the next.
        """
        batch_uids = {holder.batch_uid for holder in holders}
        if len(batch_uids) == 1:
            return next(iter(batch_uids))
        return self._database_service.get_earliest_batch(session, batch_uids).uid

    def _delete_or_change_batch_to_default_for_items(
        self,
        batch: UUID | Batch | DatabaseBatch,
        schema: ItemSchema,
        default_batch_uid: UUID,
        session: Session,
        only_non_selected=False,
    ) -> None:
        batch_uid = self._database_service.get_batch(session, batch).uid
        items = self._database_service.get_items(
            batch=batch_uid,
            schema=schema,
            selected=False if only_non_selected else None,
            session=session,
        )
        for item in items:
            if self._held_by_other_batches(item, batch_uid):
                item.batch_uid = default_batch_uid
            else:
                if item.selected:
                    # If the item is selected and related to items in other batches,
                    # the relations needs to be re-valuated
                    was_valid = self._validation_service.item_is_valid_for_now(
                        item, session
                    )
                    item.selected = False
                    self._validation_service.validate_item_relations(item, session)
                    self._review_service.item_validity_changed(
                        item.uid,
                        was_valid,
                        self._validation_service.item_is_valid_for_now(item, session),
                        session=session,
                    )
                session.delete(item)
        session.commit()

    def reset(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
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
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.initialized:
                error = (
                    f"Can only set {BatchStatus.INITIALIZED} batch as "
                    f"{BatchStatus.METADATA_SEARCHING}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.METADATA_SEARCHING
            batch.status_message = None
            self._logger.info(f"Batch {batch.uid} set as {batch.status}.")
            session.commit()
            return batch.model

    def set_as_search_complete(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
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
            self._logger.info(f"Batch {batch.uid} set as {batch.status}.")
            session.commit()
            return batch.model

    def set_as_pre_processing(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
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
            self._logger.info(f"Batch {batch.uid} set as pre-processing.")
            session.commit()
            return batch.model

    def set_as_pre_processed(
        self,
        batch: UUID | Batch | DatabaseBatch,
        force: bool = False,
        session: Session | None = None,
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
            # What the import said it would not bring in has now been brought
            # in, so every item held to a lower bar until this moment answers
            # for itself from here on. Nothing happened to any of them, so
            # nothing else would notice: the batch is swept once, here.
            flagged = self._review_service.flag_invalid_review_units(
                batch.project.dataset_uid, batch.uid, session=session
            )
            self._logger.info(
                f"Batch {batch.uid} set as pre-processed, "
                f"with {flagged} review units holding something not valid."
            )
            session.commit()
            return batch.model

    def set_as_post_processed(
        self,
        batch: UUID | Batch | DatabaseBatch,
        force: bool = False,
        session: Session | None = None,
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
            self._logger.info(f"Batch {batch.uid} set as post-processed.")
            session.commit()
            return batch.model

    def set_as_post_processing(
        self,
        batch: UUID | Batch | DatabaseBatch,
        force: bool = False,
        session: Session | None = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.image_pre_processing_complete and not force:
                error = (
                    f"Can only set {BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE} "
                    f"batch as {BatchStatus.IMAGE_POST_PROCESSING}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.IMAGE_POST_PROCESSING
            self._logger.info(f"Batch {batch.uid} set as post-processing.")
            return batch.model

    def set_as_storing(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            # Curated is what a batch is when the project it belongs to is
            # completed, which is what writes the images out; storing again is
            # how an attempt that failed part-way is resumed.
            if batch.status not in (
                BatchStatus.LOCKED,
                BatchStatus.IMAGE_STORING,
            ):
                error = (
                    f"Can only set {BatchStatus.LOCKED} or "
                    f"{BatchStatus.IMAGE_STORING} batch as "
                    f"{BatchStatus.IMAGE_STORING}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.IMAGE_STORING
            self._logger.info(f"Batch {batch.uid} set as storing.")
            session.commit()
            return batch.model

    def image_that_failed_to_store(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
    ) -> DatabaseImage | None:
        """Return an image of the batch that failed to store, if there is one.

        A batch that has one is missing that image from the dataset in the outbox,
        and is thus not complete. The image is stored by retrying it, or excluded
        from the batch by deselecting it.

        Parameters
        ----------
        batch: UUID | Batch | DatabaseBatch
            Batch to look for an image that failed to store in.
        session: Session | None = None
            Session to use.
        """
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            return self._database_service.get_first_image_for_batch(
                session,
                batch_uid=batch.uid,
                include_status=[ImageStatus.STORING_FAILED],
                selected=True,
            )

    def set_as_completed(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
    ) -> Batch:
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.image_storing:
                error = (
                    f"Can only set {BatchStatus.IMAGE_STORING} batch as "
                    f"{BatchStatus.COMPLETED}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            failed_image = self.image_that_failed_to_store(batch, session)
            if failed_image is not None:
                error = (
                    f"Can not set batch {batch.uid} as {BatchStatus.COMPLETED}, "
                    f"image {failed_image.uid} failed to store. Retry the image to "
                    f"store it, or deselect it to complete the batch without it."
                )
                raise NotAllowedActionError(error)
            batch.status = BatchStatus.COMPLETED
            self._logger.info(f"Batch {batch.uid} set as completed.")
            self._handle_project_status(batch.project)
            session.commit()
            return batch.model

    def set_as_locked(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
    ) -> Batch:
        """Finish curating a batch: everything in it is valid, and now locked.

        Nothing is written to the outbox yet — that happens when the project is
        completed, so that a batch reopened before then leaves nothing behind in
        a bundle that has been handed over.

        An item that is not valid blocks this, rather than being quietly left
        out: it is either curated until it is valid or taken out of the project
        deliberately.
        """
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if not batch.image_post_processing_complete:
                error = (
                    f"Can only set {BatchStatus.IMAGE_POST_PROCESSING_COMPLETE} "
                    f"batch as {BatchStatus.LOCKED}, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            validation = self._validation_service.get_validation_for_batch(batch)
            if not validation.valid:
                named = ", ".join(
                    item.identifier for item in validation.non_valid_items[:10]
                )
                error = (
                    f"Can not set batch {batch.uid} as "
                    f"{BatchStatus.LOCKED}: "
                    f"{len(validation.non_valid_items)} items are not valid "
                    f"({named}). Curate them, or take them out of the project."
                )
                raise NotAllowedActionError(error)
            self._lock_contents(batch, True, session)
            batch.status = BatchStatus.LOCKED
            self._logger.info(f"Batch {batch.uid} set as locked.")
            self._handle_project_status(batch.project)
            session.commit()
            return batch.model

    def reopen(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
    ) -> Batch:
        """Take a curated batch back into curation, unlocking what it holds.

        Only while the project has not been exported: after that the bundle has
        been handed over, and what is in it cannot be taken back.
        """
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            if batch.status != BatchStatus.LOCKED:
                error = (
                    f"Can only reopen a {BatchStatus.LOCKED} batch, was {batch.status}"
                )
                raise NotAllowedActionError(error)
            if batch.project.status not in (
                ProjectStatus.IN_PROGRESS,
                ProjectStatus.COMPLETED,
            ):
                error = (
                    f"Can not reopen batch {batch.uid}: project "
                    f"{batch.project.uid} is {batch.project.status}."
                )
                raise NotAllowedActionError(error)
            self._lock_contents(batch, False, session)
            batch.status = BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
            self._logger.info(f"Batch {batch.uid} reopened for curation.")
            self._handle_project_status(batch.project)
            session.commit()
            return batch.model

    def _lock_contents(
        self, batch: DatabaseBatch, locked: bool, session: Session
    ) -> None:
        """Lock or unlock everything the batch holds, attributes included."""
        items = (
            item
            for schema in self._schema_service.items.values()
            for item in self._database_service.get_items(
                session=session, schema=schema, batch=batch
            )
        )
        for item in items:
            item.locked = locked
            for attribute in item.attributes:
                attribute.locked = locked

    def set_as_failed(
        self,
        batch: UUID | Batch | DatabaseBatch,
        session: Session | None = None,
        message: str | None = None,
    ) -> Batch:
        """Set batch as failed, with an optional message for the user."""
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            batch.status = BatchStatus.FAILED
            batch.status_message = message[:512] if message is not None else None
            self._logger.info(f"Batch {batch.uid} set as failed: {message}")
            session.commit()
            return batch.model

    def _handle_project_status(self, project: DatabaseProject):
        batches = project.batches
        # Curated counts as done for the project: the images are written when
        # the project is completed, so waiting for them here would be waiting
        # for something this decides to start.
        any_all_completed_batch_in_project = all(
            batch.status in (BatchStatus.LOCKED, BatchStatus.COMPLETED)
            for batch in batches
        )
        # Nested rather than chained: written as `if done and not completed /
        # elif completed`, a project that is done and already completed falls to
        # the second branch and is put back in progress by the very call that
        # finished it.
        if any_all_completed_batch_in_project:
            if project.status != ProjectStatus.COMPLETED:
                project.status = ProjectStatus.COMPLETED
        elif project.status == ProjectStatus.COMPLETED:
            project.status = ProjectStatus.IN_PROGRESS
