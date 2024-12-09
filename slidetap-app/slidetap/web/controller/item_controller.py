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

"""Controller for handling attributes."""

from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slidetap.model.table import TableRequest
from slidetap.serialization.common import ItemReferenceModel
from slidetap.serialization.item import ItemModel
from slidetap.serialization.table import TableRequestModel
from slidetap.serialization.validation import ItemValidationModel
from slidetap.services import ItemService, LoginService
from slidetap.services.preview_service import PreviewService
from slidetap.services.processing_service import ProcessingService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService
from slidetap.web.controller.controller import SecuredController


class ItemController(SecuredController):
    """Controller for items."""

    def __init__(
        self,
        login_service: LoginService,
        item_service: ItemService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        preview_service: PreviewService,
        processing_service: ProcessingService,
    ):
        super().__init__(login_service, Blueprint("item", __name__))
        self._item_model = ItemModel()
        self._table_request_model = TableRequestModel()

        @self.blueprint.route(
            "/<uuid:item_uid>",
            methods=["GET"],
        )
        def get_item(item_uid: UUID) -> Response:
            """
            Parameters
            ----------
            item_uid: UUID


            Returns
            ----------
            Response
            """
            current_app.logger.debug(f"Get item {item_uid}.")
            item = item_service.get(item_uid)
            if item is None:
                current_app.logger.error(f"Item {item_uid} not found.")
                return self.return_not_found()
            return self.return_json(self._item_model.dump(item))

        @self.blueprint.route(
            "/<uuid:item_uid>/preview",
            methods=["GET"],
        )
        def preview_item(item_uid: UUID) -> Response:
            """
            Return preview string for item.

            Parameters
            ----------
            item_uid: UUID


            Returns
            ----------
            Response
            """
            current_app.logger.debug(f"Preview item {item_uid}.")
            preview = preview_service.get_preview(item_uid)
            if preview is None:
                current_app.logger.error(f"Item {item_uid} not found.")
                return self.return_not_found()
            return self.return_json({"preview": preview})

        @self.blueprint.route(
            "/<uuid:item_uid>/select",
            methods=["POST"],
        )
        def select_item(item_uid: UUID) -> Response:
            """Select or de-select item id.

            Parameters
            ----------
            item_uid: UUID
                Id of item to select.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.debug(f"Select item {item_uid}.")
            value = request.args["value"] == "true"
            item = item_service.select(item_uid, value)
            if item is None:
                return self.return_not_found()
            return self.return_ok()

        @self.blueprint.route(
            "/<uuid:item_uid>",
            methods=["POST"],
        )
        def save_item(item_uid: UUID) -> Response:
            """Update item with specified id.

            Parameters
            ----------
            item_uid: UUID
                Id of item to update.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.debug(f"Update item {item_uid}.")
            item_schema = item_service.get_schema_for_item(item_uid)
            if item_schema is None:
                return self.return_not_found()
            item = self._item_model.load(request.get_json())
            item = item_service.update(item)
            if item is None:
                return self.return_not_found()
            return self.return_json(self._item_model.dump(item))

        @self.blueprint.route(
            "/<uuid:item_uid>/validation",
            methods=["GET"],
        )
        def get_validation(item_uid: UUID) -> Response:
            """Get validation of item.

            Parameters
            ----------
            item_uid: UUID
                Id of item to get validation for.

            Returns
            ----------
            Response
                Json-response of validation.
            """
            validation = validation_service.get_validation_for_item(item_uid)
            if validation is None:
                return self.return_not_found()
            current_app.logger.debug(
                f"Get validation for item {item_uid}, {validation}"
            )
            return self.return_json(ItemValidationModel().dump(validation))

        @self.blueprint.route(
            "/add/<uuid:schema_uid>/project/<uuid:project_uid>",
            methods=["POST"],
        )
        def add_item(schema_uid: UUID, project_uid: UUID) -> Response:
            """Update item with specified id.

            Parameters
            ----------
            item_uid: UUID
                Id of item to update.

            Returns
            ----------
            Response
                OK if successful.
            """

            current_app.logger.debug("Add item.")
            item_schema = schema_service.get_item(schema_uid)
            if item_schema is None:
                return self.return_not_found()
            current_app.logger.debug(f"Item schema: {item_schema.uid}")
            item = self._item_model.load(request.get_json())
            item = item_service.add(item)
            return self.return_json(self._item_model.dump(item))

        @self.blueprint.route(
            "/create/<uuid:schema_uid>/project/<uuid:project_uid>",
            methods=["POST"],
        )
        def create_item(schema_uid: UUID, project_uid: UUID) -> Response:
            """Create item.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.debug("Create item.")
            item = item_service.create(schema_uid, project_uid)
            if item is None:
                return self.return_not_found()
            return self.return_json(self._item_model.dump(item))

        @self.blueprint.route(
            "/<uuid:item_uid>/copy",
            methods=["POST"],
        )
        def copy_item(item_uid: UUID) -> Response:
            """Copy item with specified id.

            Parameters
            ----------
            item_uid: UUID
                Id of item to copy.

            Returns
            ----------
            Response

            """
            current_app.logger.debug(f"Copy item {item_uid}.")
            item = item_service.copy(item_uid)
            if item is None:
                current_app.logger.error(f"Item {item_uid} not found.")
                return self.return_not_found()
            return self.return_json(self._item_model.dump(item))

        @self.blueprint.route(
            "/schema/<uuid:item_schema_uid>/project/<uuid:project_uid>/items",
            methods=["GET", "POST"],
        )
        def get_items(project_uid: UUID, item_schema_uid: UUID) -> Response:
            """Get items of specified type from project.

            Parameters
            ----------
            project_uid: UUID
                Id of project to get samples from.
            item_schema_uid: UUID
                Item schema to get.


            Returns
            ----------
            Response
                Json-response of items.
            """
            if request.method == "POST":
                try:
                    table_request = self._table_request_model.load(request.get_json())
                except Exception:
                    table_request = TableRequest()
            else:
                table_request = TableRequest()
            items = item_service.get_for_schema(
                item_schema_uid,
                project_uid,
                table_request.start,
                table_request.size,
                table_request.identifier_filter,
                table_request.attribute_filters,
                table_request.sorting,
                table_request.included,
                table_request.valid,
            )
            count = item_service.get_count_for_schema(
                item_schema_uid,
                project_uid,
                table_request.identifier_filter,
                table_request.attribute_filters,
                table_request.included,
                table_request.valid,
            )
            if items is None:
                return self.return_not_found()
            items = list(items)
            if len(items) == 0:
                return self.return_json({"items": {}, "count": count})
            return self.return_json(
                {
                    "items": [self._item_model.dump(item) for item in items],
                    "count": count,
                }
            )

        @self.blueprint.route(
            "/schema/<uuid:item_schema_uid>/project/<uuid:project_uid>/references",
            methods=["GET"],
        )
        def get_references(item_schema_uid: UUID, project_uid: UUID) -> Response:
            """Get items of schema.

            Parameters
            ----------
            item_schema_uid: UUID
                Id of item schema to get items of.
            project_uid: UUID
                Id of project to get items of.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.debug(f"Get items of schema {item_schema_uid}.")
            item_schema = schema_service.get_item(item_schema_uid)
            if item_schema is None:
                return self.return_not_found()
            items = item_service.get_for_schema(item_schema_uid, project_uid)
            model = ItemReferenceModel()
            return self.return_json({item.uid: model.dump(item) for item in items})

        @self.blueprint.route("/retry", methods=["POST"])
        def retry() -> Response:
            session = login_service.get_current_session()
            image_uids = request.get_json()
            for image_uid in image_uids:
                processing_service.retry_image(session, UUID(image_uid))
            return self.return_ok()
