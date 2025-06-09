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
from typing import Set
from uuid import UUID

from flask import Blueprint
from flask.wrappers import Response

from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ItemSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.serialization import (
    AttributeSchemaModel,
    DatasetSchemaModel,
    ItemSchemaModel,
    RootSchemaModel,
)
from slidetap.services import SchemaService
from slidetap.web.controller.controller import SecuredController
from slidetap.web.services import LoginService


class SchemaController(SecuredController):
    """Controller for schemas."""

    def __init__(
        self,
        login_service: LoginService,
        schema_service: SchemaService,
    ):
        super().__init__(login_service, Blueprint("schema", __name__))
        self._root_model = RootSchemaModel()
        self._attribute_model = AttributeSchemaModel()
        self._item_model = ItemSchemaModel()
        self._project_model = DatasetSchemaModel()

        @self.blueprint.route("/root", methods=["GET"])
        def get_root_schema() -> Response:
            schema = schema_service.get_root()
            return self.return_json(self._root_model.dump(schema))

        @self.blueprint.route("/attributes/<uuid:schema_uid>", methods=["GET"])
        def get_attribute_schemas(schema_uid: UUID) -> Response:
            schemas = schema_service.get_attributes(schema_uid)
            return self.return_json(
                [self._attribute_model.dump(schema) for schema in schemas]
            )

        @self.blueprint.route("/attribute/<uuid:attribute_schema_uid>", methods=["GET"])
        def get_attribute_schema(attribute_schema_uid: UUID) -> Response:
            schema = schema_service.get_attribute(attribute_schema_uid)
            if schema is None:
                return self.return_not_found()
            return self.return_json(self._attribute_model.dump(schema))

        @self.blueprint.route("/item/<uuid:item_schema_uid>", methods=["GET"])
        def get_item_schema(item_schema_uid: UUID) -> Response:
            schema = schema_service.get_item(item_schema_uid)
            if schema is None:
                return self.return_json(None)
            return self.return_json(self._item_model.dump(schema))

        @self.blueprint.route("/item/<uuid:item_schema_uid>/hierarchy", methods=["GET"])
        def get_item_schema_hierarchy(item_schema_uid: UUID) -> Response:
            def recursive(schema: ItemSchema) -> Set[UUID]:
                schemas = set([schema.uid])

                if isinstance(schema, SampleSchema):
                    for child in schema.children:
                        schemas.update(
                            recursive(schema_service.get_item(child.child_uid))
                        )
                elif isinstance(schema, AnnotationSchema):
                    for image in schema.images:
                        schemas.update(
                            recursive(schema_service.get_item(image.image_uid))
                        )
                elif isinstance(schema, ObservationSchema):
                    for sample in schema.samples:
                        schemas.update(
                            recursive(schema_service.get_item(sample.sample_uid))
                        )
                    for annotation in schema.annotations:
                        schemas.update(
                            recursive(
                                schema_service.get_item(annotation.annotation_uid)
                            )
                        )
                    for image in schema.images:
                        schemas.add(schema_service.get_item(image.image_uid).uid)

                return schemas

            schema = schema_service.get_item(item_schema_uid)
            schema_uids = recursive(schema)

            return self.return_json(
                [
                    self._item_model.dump(schema_service.get_item(schema_uid))
                    for schema_uid in schema_uids
                ]
            )
