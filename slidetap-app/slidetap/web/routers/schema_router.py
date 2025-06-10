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

"""FastAPI router for handling schemas."""
import logging
from http import HTTPStatus
from typing import List, Optional, Set
from uuid import UUID

from fastapi import HTTPException

from slidetap.model.schema.attribute_schema import AttributeSchema
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    ItemSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.model.schema.root_schema import RootSchema
from slidetap.services import SchemaService
from slidetap.web.routers.router import SecuredRouter


class SchemaRouter(SecuredRouter):
    """FastAPI router for schemas."""

    def __init__(
        self,
        schema_service: SchemaService,
    ):
        self._schema_service = schema_service
        self._logger = logging.getLogger(__name__)
        super().__init__()

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all schema routes."""

        @self.router.get("/root")
        async def get_root_schema(user=self.auth_dependency()) -> RootSchema:
            """Get the root schema.

            Returns
            ----------
            RootSchema
                The root schema
            """
            schema = self._schema_service.get_root()
            return schema

        @self.router.get("/attributes")
        async def get_attribute_schemas(
            user=self.auth_dependency(),
        ) -> List[AttributeSchema]:
            """Get attribute schemas for a schema.

            Parameters
            ----------
            schema_uid: UUID
                ID of the schema

            Returns
            ----------
            List[AttributeSchema]
                List of attribute schemas
            """
            schemas = self._schema_service.get_attributes(
                self._schema_service.get_root().uid
            )
            return list(schemas)

        @self.router.get("/attribute/{attribute_schema_uid}")
        async def get_attribute_schema(
            attribute_schema_uid: UUID, user=self.auth_dependency()
        ) -> AttributeSchema:
            """Get attribute schema by ID.

            Parameters
            ----------
            attribute_schema_uid: UUID
                ID of the attribute schema

            Returns
            ----------
            AttributeSchema
                The requested attribute schema
            """
            schema = self._schema_service.get_attribute(attribute_schema_uid)
            if schema is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Attribute schema {attribute_schema_uid} not found",
                )
            return schema

        @self.router.get("/item/{item_schema_uid}")
        async def get_item_schema(
            item_schema_uid: UUID, user=self.auth_dependency()
        ) -> Optional[ItemSchema]:
            """Get item schema by ID.

            Parameters
            ----------
            item_schema_uid: UUID
                ID of the item schema

            Returns
            ----------
            Optional[ItemSchema]
                The requested item schema, or None if not found
            """
            schema = self._schema_service.get_item(item_schema_uid)
            return schema

        @self.router.get("/item/{item_schema_uid}/hierarchy")
        async def get_item_schema_hierarchy(
            item_schema_uid: UUID, user=self.auth_dependency()
        ) -> List[ItemSchema]:
            """Get item schema hierarchy.

            Parameters
            ----------
            item_schema_uid: UUID
                ID of the item schema

            Returns
            ----------
            List[ItemSchema]
                List of schemas in the hierarchy
            """

            def recursive(schema: ItemSchema) -> Set[UUID]:
                schemas = set([schema.uid])

                if isinstance(schema, SampleSchema):
                    for child in schema.children:
                        child_schema = self._schema_service.get_item(child.child_uid)
                        if child_schema:
                            schemas.update(recursive(child_schema))
                elif isinstance(schema, AnnotationSchema):
                    for image in schema.images:
                        image_schema = self._schema_service.get_item(image.image_uid)
                        if image_schema:
                            schemas.update(recursive(image_schema))
                elif isinstance(schema, ObservationSchema):
                    for sample in schema.samples:
                        sample_schema = self._schema_service.get_item(sample.sample_uid)
                        if sample_schema:
                            schemas.update(recursive(sample_schema))
                    for annotation in schema.annotations:
                        annotation_schema = self._schema_service.get_item(
                            annotation.annotation_uid
                        )
                        if annotation_schema:
                            schemas.update(recursive(annotation_schema))
                    for image in schema.images:
                        image_schema = self._schema_service.get_item(image.image_uid)
                        if image_schema:
                            schemas.add(image_schema.uid)

                return schemas

            schema = self._schema_service.get_item(item_schema_uid)
            if schema is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Item schema {item_schema_uid} not found",
                )

            schema_uids = recursive(schema)
            schemas = []
            for schema_uid in schema_uids:
                item_schema = self._schema_service.get_item(schema_uid)
                if item_schema:
                    schemas.append(item_schema)

            return schemas
