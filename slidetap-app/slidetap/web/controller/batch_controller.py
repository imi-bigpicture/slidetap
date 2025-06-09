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

"""Controller for handling batches and items in batches."""
from typing import Optional
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response
from werkzeug.datastructures import FileStorage

from slidetap.model import Batch, BatchStatus
from slidetap.services import (
    BatchService,
    DatabaseService,
    SchemaService,
    ValidationService,
)
from slidetap.web.controller.controller import SecuredController
from slidetap.web.services import (
    ImageExportService,
    ImageImportService,
    LoginService,
    MetadataImportService,
)


class BatchController(SecuredController):
    """Controller for batches."""

    def __init__(
        self,
        login_service: LoginService,
        batch_service: BatchService,
        validation_service: ValidationService,
        schema_service: SchemaService,
        database_service: DatabaseService,
        metadata_import_service: MetadataImportService,
        image_import_service: ImageImportService,
        image_export_service: ImageExportService,
    ):
        super().__init__(login_service, Blueprint("batch", __name__))
        self._batch_service = batch_service
        self._validation_service = validation_service
        self._schema_service = schema_service
        self._database_service = database_service
        self._metadata_import_service = metadata_import_service
        self._image_import_service = image_import_service
        self._image_export_service = image_export_service

        @self.blueprint.route("/create", methods=["Post"])
        def create_batch() -> Response:
            """Create a batch based on parameters in form.

            Returns
            ----------
            Response
                Response with created batch's id.
            """

            batch = Batch.model_validate(request.get_json())
            try:
                batch = batch_service.create(batch)
                current_app.logger.debug(f"Created batch {batch.uid}")
                return self.return_json(batch.model_dump(mode="json", by_alias=True))
            except ValueError:
                current_app.logger.error(
                    "Failed to parse file due to error", exc_info=True
                )
                return self.return_bad_request()

        @self.blueprint.route("", methods=["GET"])
        def get_batches() -> Response:
            """Get status of registered batches.

            Returns
            ----------
            Response
                Json-response of registered batches
            """
            project_uid = request.args.get("project_uid", None)
            status = request.args.get("status", None)
            batches = batch_service.get_all(
                project_uid=UUID(project_uid) if project_uid is not None else None,
                status=BatchStatus(status) if status is not None else None,
            )
            return self.return_json(
                [batch.model_dump(mode="json", by_alias=True) for batch in batches]
            )

        @self.blueprint.route("/<uuid:batch_uid>", methods=["Post"])
        def update(batch_uid: UUID) -> Response:
            """Update batch specified by id with data from form.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch to update

            Returns
            ----------
            Response
                OK response if successful.
            """
            batch = Batch.model_validate(request.get_json())
            try:
                batch = batch_service.update(batch)
                if batch is None:
                    return self.return_not_found()
                current_app.logger.debug(f"Updated batch {batch.uid, batch.name}")
                return self.return_json(batch.model_dump(mode="json", by_alias=True))
            except ValueError:
                current_app.logger.error(
                    "Failed to parse file due to error", exc_info=True
                )
                return self.return_bad_request()

        @self.blueprint.route("<uuid:batch_uid>/uploadFile", methods=["POST"])
        def upload_batch_file(batch_uid: UUID) -> Response:
            """Search for metadata and images for batch specified by id
            using search criteria specified in posted file.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch to search.

            Returns
            ----------
            Response
                OK response if successful.
            """
            if "file" not in request.files:
                current_app.logger.error("No file in request.")
                return self.return_bad_request()
            file = request.files["file"]
            try:
                batch = self._start_metadata_search(batch_uid, file)
                if batch is None:
                    current_app.logger.error(f"No batch found with uid {batch_uid}.")
                    return self.return_not_found()
            except ValueError:
                current_app.logger.error(
                    "Failed to parse file due to error", exc_info=True
                )
                return self.return_bad_request()
            return self.return_json(batch.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/<uuid:batch_uid>/pre_process", methods=["POST"])
        def pre_process(batch_uid: UUID) -> Response:
            """Preprocess images for batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.info(f"Pre-processing batch {batch_uid}.")
            batch = self._pre_process_batch(batch_uid)
            if batch is None:
                return self.return_not_found()
            return self.return_json(batch.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/<uuid:batch_uid>/process", methods=["POST"])
        def process(batch_uid: UUID) -> Response:
            """Start batch specified by id. Accepts selected items in
             batch and start downloading images.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.info(f"Processing batch {batch_uid}.")
            batch = self._process_batch(batch_uid)
            if batch is None:
                return self.return_not_found()
            return self.return_json(batch.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/<uuid:batch_uid>/complete", methods=["POST"])
        def complete(batch_uid: UUID) -> Response:
            """Complete batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.info(f"Completing batch {batch_uid}.")
            batch = batch_service.set_as_completed(batch_uid)
            if batch is None:
                return self.return_not_found()
            return self.return_json(batch.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/<uuid:batch_uid>", methods=["GET"])
        def get_batch(batch_uid: UUID) -> Response:
            """Get status of batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Response
                Json-response of batch.
            """
            batch = batch_service.get(batch_uid)
            if batch is None:
                return self.return_not_found()
            return self.return_json(batch.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("<uuid:batch_uid>", methods=["DELETE"])
        def delete_batch(batch_uid: UUID) -> Response:
            """Delete batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch.

            Returns
            ----------
            Response
                Ok if successful.
            """
            batch = batch_service.delete(batch_uid)
            if batch is None:
                return self.return_not_found()
            if not batch.status == BatchStatus.DELETED:
                return self.return_bad_request()
            return self.return_ok()

        @self.blueprint.route("<uuid:batch_uid>/validation", methods=["GET"])
        def get_validation(batch_uid: UUID) -> Response:
            """Get validation of batch specified by id.

            Parameters
            ----------
            batch_uid: UUID
                Id of batch to get validation of.

            Returns
            ----------
            Response
                OK if successful.
            """
            validation = validation_service.get_validation_for_batch(batch_uid)
            current_app.logger.debug(f"Validation of batch {batch_uid}: {validation}")
            return self.return_json(validation.model_dump(mode="json", by_alias=True))

    def _start_metadata_search(
        self, batch_uid: UUID, file: FileStorage
    ) -> Optional[Batch]:
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
