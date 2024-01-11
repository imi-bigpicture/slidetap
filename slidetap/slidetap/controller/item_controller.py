"""Controller for handling attributes."""
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slidetap.controller.controller import Controller
from slidetap.database.project import Item
from slidetap.serialization.common import ItemReferenceModel
from slidetap.serialization.item import ItemModelFactory
from slidetap.services import ItemService, LoginService
from slidetap.services.schema_service import SchemaService


class ItemController(Controller):
    """Controller for items."""

    def __init__(
        self,
        login_service: LoginService,
        item_service: ItemService,
        schema_service: SchemaService,
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
            model = model_factory.create(item_schema)()
            item = model.load(request.get_json())
            return self.return_json(model.dump(item))

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
            model = model_factory.create(item_schema)(
                context={"project_uid": project_uid}
            )
            item = model.load(request.get_json())
            current_app.logger.debug(f"Item: {item}")
            if item is None:
                return self.return_not_found()
            assert isinstance(item, Item)
            item_service.add(item)
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
            model = model_factory.create(item.schema)()
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

        @self.blueprint.route(
            "/schema/<uuid:schema_uid>/project/<uuid:project_uid>",
            methods=["GET"],
        )
        def get_of_schema(schema_uid: UUID, project_uid: UUID) -> Response:
            """Get items of schema.

            Parameters
            ----------
            schema_uid: UUID
                Id of schema to get items of.
            project_uid: UUID
                Id of project to get items of.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.debug(f"Get items of schema {schema_uid}.")
            item_schema = schema_service.get_item(schema_uid)
            if item_schema is None:
                return self.return_not_found()
            items = item_service.get_of_schema(schema_uid, project_uid)
            model = ItemReferenceModel()
            return self.return_json(model.dump(items, many=True))
