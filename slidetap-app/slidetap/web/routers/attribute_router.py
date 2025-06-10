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

"""FastAPI router for handling attributes."""
import logging
from typing import Dict, Iterable
from uuid import UUID

from fastapi import HTTPException

from slidetap.model.attribute import Attribute, attribute_factory
from slidetap.model.mapper import MappingItem
from slidetap.services import (
    AttributeService,
    MapperService,
    SchemaService,
    ValidationService,
)
from slidetap.web.routers.router import SecuredRouter


class AttributeRouter(SecuredRouter):
    """FastAPI router for attributes."""

    def __init__(
        self,
        attribute_service: AttributeService,
        schema_service: SchemaService,
        mapper_service: MapperService,
        validation_service: ValidationService,
    ):
        self._attribute_service = attribute_service
        self._schema_service = schema_service
        self._mapper_service = mapper_service
        self._validation_service = validation_service
        self._logger = logging.getLogger(__name__)
        super().__init__()

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all attribute routes."""

        @self.router.get("/attribute/{attribute_uid}")
        async def get_attribute(
            attribute_uid: UUID, user=self.auth_dependency()
        ) -> Attribute:
            """Get attribute by ID."""
            self._logger.debug(f"Get attribute {attribute_uid}.")
            attribute = self._attribute_service.get(attribute_uid)
            if attribute is None:
                self._logger.error(f"Attribute {attribute_uid} not found.")
                raise HTTPException(status_code=404, detail="Attribute not found")
            return attribute

        @self.router.post("/attribute/{attribute_uid}")
        async def update_attribute(
            attribute_uid: UUID, attribute: Attribute, user=self.auth_dependency()
        ) -> Attribute:
            """Update attribute."""
            self._logger.debug(f"Update attribute {attribute_uid}.")
            updated_attribute = self._attribute_service.update(attribute)
            if updated_attribute is None:
                raise HTTPException(status_code=404, detail="Attribute not found")
            return attribute

        @self.router.post("/create/{attribute_schema_uid}")
        async def create_attribute(
            attribute_schema_uid: UUID,
            attribute_data: Dict,
            user=self.auth_dependency(),
        ) -> Attribute:
            """Create attribute."""
            self._logger.debug("Create attribute.")
            attribute_schema = self._schema_service.get_attribute(attribute_schema_uid)
            assert attribute_schema is not None
            attribute = attribute_factory(attribute_data)
            attribute = self._attribute_service.create(attribute)
            return attribute

        @self.router.get("/attribute/{attribute_uid}/mapping")
        async def get_mapping(
            attribute_uid: UUID, user=self.auth_dependency()
        ) -> MappingItem:
            """Get mapping for attribute."""
            self._logger.debug(f"Get mapping for attribute {attribute_uid}.")
            attribute = self._attribute_service.get(attribute_uid)
            if attribute is None or attribute.mappable_value is None:
                raise HTTPException(status_code=404, detail="Attribute not found")
            if attribute.mapping_item_uid is None:
                mapping_item = self._mapper_service.get_mapping_for_attribute(attribute)
            else:
                mapping_item = self._mapper_service.get_mapping(
                    attribute.mapping_item_uid
                )
            if mapping_item is None:
                raise HTTPException(status_code=404, detail="Mapping not found")
            return mapping_item

        @self.router.get("/schema/{attribute_schema_uid}")
        async def get_attributes_for_schema(
            attribute_schema_uid: UUID, user=self.auth_dependency()
        ) -> Iterable[Attribute]:
            """Get attributes for schema."""
            attributes = self._attribute_service.get_for_schema(attribute_schema_uid)
            return attributes
