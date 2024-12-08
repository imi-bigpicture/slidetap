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

"""Service for accessing schemas."""

from typing import Iterable
from uuid import UUID

from slidetap.database import (
    DatabaseAttributeSchema,
    DatabaseItemSchema,
)
from slidetap.database.schema.root_schema import DatabaseRootSchema
from slidetap.model.schema.attribute_schema import AttributeSchema
from slidetap.model.schema.item_schema import ItemSchema
from slidetap.model.schema.root_schema import RootSchema


class SchemaService:
    """Schema service should be used to interface with schemas."""

    def __init__(self, root_schema_uid: UUID):
        self._root_schema_uid = root_schema_uid

    def get_attributes(self, schema_uid: UUID) -> Iterable[AttributeSchema]:
        return (
            schema.model
            for schema in DatabaseAttributeSchema.get_for_schema(schema_uid)
        )

    def get_attribute(self, attribute_schema_uid: UUID) -> AttributeSchema:
        return DatabaseAttributeSchema.get(attribute_schema_uid).model

    def get_item(self, item_schema_uid: UUID) -> ItemSchema:
        return DatabaseItemSchema.get(item_schema_uid).model

    def get_root(self) -> RootSchema:
        return DatabaseRootSchema.get(self._root_schema_uid).model
