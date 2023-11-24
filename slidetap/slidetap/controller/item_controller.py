"""Controller for handling attributes."""
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
            return self.return_json(ItemModelFactory().create(item.schema)().dump(item))

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
            value = request.args["value"] == "true"
            item = item_service.select(item_uid, value)
            if item is None:
                return self.return_not_found()
            return self.return_ok()
