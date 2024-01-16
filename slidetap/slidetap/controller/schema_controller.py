"""Controller for handling attributes."""
from uuid import UUID

from flask import Blueprint
from flask.wrappers import Response

from slidetap.controller.controller import SecuredController
from slidetap.serialization import AttributeSchemaModel
from slidetap.serialization.schema import ItemSchemaOneOfModel
from slidetap.services import LoginService
from slidetap.services.schema_service import SchemaService


class SchemaController(SecuredController):
    """Controller for schemas."""

    def __init__(
        self,
        login_service: LoginService,
        schema_service: SchemaService,
    ):
        super().__init__(login_service, Blueprint("schema", __name__))

        @self.blueprint.route("/attributes/<uuid:schema_uid>", methods=["GET"])
        def get_attribute_schemas(schema_uid: UUID) -> Response:
            schemas = schema_service.get_attributes(schema_uid)
            return self.return_json(AttributeSchemaModel().dump(schemas, many=True))

        @self.blueprint.route("/attribute/<uuid:attribute_schema_uid>", methods=["GET"])
        def get_attribute_schema(attribute_schema_uid: UUID) -> Response:
            schema = schema_service.get_attribute(attribute_schema_uid)
            return self.return_json(AttributeSchemaModel().dump(schema))

        @self.blueprint.route("/items/<uuid:schema_uid>", methods=["GET"])
        def get_item_schemas(schema_uid: UUID) -> Response:
            schemas = schema_service.get_items(schema_uid)
            return self.return_json(ItemSchemaOneOfModel().dump_many(schemas))

        @self.blueprint.route("/item/<uuid:item_schema_uid>", methods=["GET"])
        def get_item_schema(item_schema_uid: UUID) -> Response:
            schema = schema_service.get_item(item_schema_uid)
            if schema is None:
                return self.return_json(None)
            return self.return_json(ItemSchemaOneOfModel().dump(schema))
