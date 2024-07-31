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

from typing import Iterable, Optional
from uuid import UUID

from slidetap.database import AttributeSchema, ItemSchema


class SchemaService:
    """Schema service should be used to interface with schemas."""

    def get_attributes(self, schema_uid: UUID) -> Iterable[AttributeSchema]:
        return AttributeSchema.get_for_schema(schema_uid)

    def get_attribute(self, attribute_schema_uid: UUID) -> Optional[AttributeSchema]:
        return AttributeSchema.get_by_uid(attribute_schema_uid)

    def get_items(self, schema_uid: UUID) -> Iterable[ItemSchema]:
        return ItemSchema.get_for_schema(schema_uid)

    def get_item(self, item_schema_uid: UUID) -> Optional[ItemSchema]:
        return ItemSchema.get_by_uid(item_schema_uid)
