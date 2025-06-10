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

"""FastAPI router for handling batches and items in batches."""
import logging
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from fastapi import File, HTTPException, Query, UploadFile

from slidetap.model import Batch, BatchStatus
from slidetap.model.validation import BatchValidation
from slidetap.services import (
    BatchService,
    DatabaseService,
    SchemaService,
    ValidationService,
)
from slidetap.web.routers.router import SecuredRouter
from slidetap.web.services import (
    ImageExportService,
    ImageImportService,
    MetadataImportService,
)


class BatchRouter(SecuredRouter):
    """FastAPI router for batches."""

    def __init__(
        self,
        batch_service: BatchService,
        validation_service: ValidationService,
        schema_service: SchemaService,
        database_service: DatabaseService,
        metadata_import_service: MetadataImportService,
        image_import_service: ImageImportService,
        image_export_service: ImageExportService,
    ):
        self._batch_service = batch_service
        self._validation_service = validation_service
        self._schema_service = schema_service
        self._database_service = database_service
        self._metadata_import_service = metadata_import_service
        self._image_import_service = image_import_service
        self._image_export_service = image_export_service
        self._logger = logging.getLogger(__name__)
        super().__init__()

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all batch routes."""

        @self.router.post("/create")
        async def create_batch(batch: Batch, user=self.auth_dependency()) -> Batch:
            """Create a batch based on parameters in request body.

            Parameters
            ----------
            batch: Batch
                Batch data to create

            Returns
            ----------
            Dict
                Response with created batch's data.
            """
            try:
                created_batch = self._batch_service.create(batch)
                self._logger.debug(f"Created batch {created_batch.uid}")
                return created_batch
            except ValueError as exception:
                self._logger.error("Failed to create batch due to error", exc_info=True)
                raise HTTPException(
                    status_code=400, detail="Failed to create batch"
                ) from exception

        @self.router.get("")
        async def get_batches(
            project_uid: Optional[UUID] = Query(None),
            status: Optional[BatchStatus] = Query(None),
            user=self.auth_dependency(),
        ) -> Iterable[Batch]:
            """Get status of registered batches.

            Parameters
            ----------
            project_uid: Optional[UUID]
                Filter by project UID
            status: Optional[BatchStatus]
                Filter by batch status

            Returns
            ----------
            List[Dict]
                List of registered batches
            """
            batches = self._batch_service.get_all(
                project_uid=project_uid,
                status=status,
            )
            return batches

        @self.router.post("/batch/{batch_uid}")
        async def update_batch(
            batch_uid: UUID, batch: Batch, user=self.auth_dependency()
        ) -> Batch:
            """Update batch specified by id with data from request body.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch to update
            batch: Batch
                Batch data to update

            Returns
            ----------
            Dict
                Updated batch data if successful.
            """
            try:
                updated_batch = self._batch_service.update(batch)
                if updated_batch is None:
                    raise HTTPException(status_code=404, detail="Batch not found")
                self._logger.debug(
                    f"Updated batch {updated_batch.uid}, {updated_batch.name}"
                )
                return updated_batch
            except ValueError as exception:
                self._logger.error("Failed to update batch due to error", exc_info=True)
                raise HTTPException(
                    status_code=400, detail="Failed to update batch"
                ) from exception

        @self.router.post("/batch/{batch_uid}/uploadFile")
        async def upload_batch_file(
            batch_uid: UUID, file: UploadFile = File(...), user=self.auth_dependency()
        ) -> Batch:
            """Search for metadata and images for batch specified by id
            using search criteria specified in uploaded file.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch to search.
            file: UploadFile
                File containing search criteria

            Returns
            ----------
            Dict
                Batch data if successful.
            """
            try:
                batch = self._start_metadata_search(batch_uid, file)
                if batch is None:
                    self._logger.error(f"No batch found with uid {batch_uid}.")
                    raise HTTPException(status_code=404, detail="Batch not found")
                return batch
            except ValueError as exception:
                self._logger.error("Failed to parse file due to error", exc_info=True)
                raise HTTPException(
                    status_code=400, detail="Failed to upload file"
                ) from exception

        @self.router.post("/batch/{batch_uid}/pre_process")
        async def pre_process(batch_uid: UUID, user=self.auth_dependency()) -> Batch:
            """Preprocess images for batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Dict
                Batch data if successful.
            """
            self._logger.info(f"Pre-processing batch {batch_uid}.")
            batch = self._pre_process_batch(batch_uid)
            if batch is None:
                raise HTTPException(status_code=404, detail="Batch not found")
            return batch

        @self.router.post("/batch/{batch_uid}/process")
        async def process(batch_uid: UUID, user=self.auth_dependency()) -> Batch:
            """Start batch specified by id. Accepts selected items in
             batch and start downloading images.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Dict
                Batch data if successful.
            """
            self._logger.info(f"Processing batch {batch_uid}.")
            batch = self._process_batch(batch_uid)
            if batch is None:
                raise HTTPException(status_code=404, detail="Batch not found")
            return batch

        @self.router.post("/batch/{batch_uid}/complete")
        async def complete(batch_uid: UUID, user=self.auth_dependency()) -> Batch:
            """Complete batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Dict
                Batch data if successful.
            """
            self._logger.info(f"Completing batch {batch_uid}.")
            batch = self._batch_service.set_as_completed(batch_uid)
            if batch is None:
                raise HTTPException(status_code=404, detail="Batch not found")
            return batch

        @self.router.get("/batch/{batch_uid}")
        async def get_batch(batch_uid: UUID, user=self.auth_dependency()) -> Batch:
            """Get status of batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Dict
                Batch data.
            """
            batch = self._batch_service.get(batch_uid)
            if batch is None:
                raise HTTPException(status_code=404, detail="Batch not found")
            return batch

        @self.router.delete("/batch/{batch_uid}")
        async def delete_batch(batch_uid: UUID, user=self.auth_dependency()):
            """Delete batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Dict
                Ok status if successful.
            """
            batch = self._batch_service.delete(batch_uid)
            if batch is None:
                raise HTTPException(status_code=404, detail="Batch not found")
            if batch.status != BatchStatus.DELETED:
                raise HTTPException(
                    status_code=400, detail="Batch could not be deleted"
                )
            return self.return_ok()

        @self.router.get("/batch/{batch_uid}/validation")
        async def get_validation(
            batch_uid: UUID, user=self.auth_dependency()
        ) -> BatchValidation:
            """Get validation of batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch to get validation of.

            Returns
            ----------
            Dict
                Validation data if successful.
            """
            validation = self._validation_service.get_validation_for_batch(batch_uid)
            self._logger.debug(f"Validation of batch {batch_uid}: {validation}")
            return validation

    def _start_metadata_search(
        self, batch_uid: UUID, file: UploadFile
    ) -> Optional[Batch]:
        """Start metadata search for a batch using uploaded file."""
        with self._database_service.get_session() as session:
            database_batch = self._database_service.get_batch(
                session,
                batch_uid,
            )
            self._batch_service.reset(database_batch, session)
            for item_schema in self._schema_service.items:
                self._database_service.delete_items(
                    session,
                    batch_uid,
                    item_schema,
                )
            batch = self._batch_service.set_as_searching(database_batch, session)
            dataset = database_batch.project.dataset.model
            session.commit()

        self._metadata_import_service.search(dataset, batch, file)
        return batch

    def _pre_process_batch(self, batch_uid: UUID) -> Optional[Batch]:
        """Pre-process a batch."""
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
        self._image_import_service.pre_process_batch(batch)
        return batch

    def _process_batch(self, batch_uid: UUID) -> Optional[Batch]:
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
        self._image_export_service.export(batch)
        return batch
