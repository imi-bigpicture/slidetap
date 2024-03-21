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
