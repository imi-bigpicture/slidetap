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

from flask import Blueprint
from flask.wrappers import Response
from slidetap.web.controller.controller import SecuredController
from slidetap.web.serialization import AttributeSchemaModel
from slidetap.web.serialization.schema import (
    AttributeSchemaOneOfModel,
    ItemSchemaOneOfModel,
)
from slidetap.web.services import LoginService
from slidetap.web.services.schema_service import SchemaService


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
            if schema is None:
                return self.return_not_found()
            return self.return_json(AttributeSchemaOneOfModel().dump(schema))

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
