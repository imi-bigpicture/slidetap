"""Controller for handling attributes."""
from typing import Mapping
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slidetap.controller.controller import Controller
from slidetap.serialization.item import ItemModelFactory
from slidetap.services import ItemService, LoginService


class ItemController(Controller):
    """Controller for items."""

    def __init__(
        self,
        login_service: LoginService,
        item_service: ItemService,
    ):
        super().__init__(login_service, Blueprint("item", __name__))
        model_factory = ItemModelFactory()

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
            return self.return_json(model_factory.create(item.schema)().dump(item))

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
        def update_item(item_uid: UUID) -> Response:
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
            model = model_factory.create(item_schema)()
            item = model.load(request.get_json())
            return self.return_json(model.dump(item))

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
            model = ItemModelFactory().create(item.schema)()
            return self.return_json(model.dump(item))

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
            return self.return_json(model_factory.create(item.schema)().dump(item))
