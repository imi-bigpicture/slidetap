"""Service for accessing attributes."""
from typing import Any, Dict, Optional, Sequence
from uuid import UUID

from slides.database import (
    Attribute,
    AttributeSchema,
    BooleanAttribute,
    BooleanAttributeSchema,
    CodeAttribute,
    CodeAttributeSchema,
    ListAttribute,
    ListAttributeSchema,
    MeasurementAttribute,
    NumericAttribute,
    NumericAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    StringAttribute,
    StringAttributeSchema,
)
from slides.model import Code, Measurement


class AttributeService:
    """Attribute service should be used to interface with attributes"""

    def get(self, attribute_uid: UUID) -> Optional[Attribute]:
        attribute = Attribute.get(attribute_uid)
        if attribute is None:
            return None
        return attribute

    def get_for_schema(self, attribute_schema_uid: UUID) -> Sequence[Attribute]:
        return Attribute.get_for_attribute_schema(attribute_schema_uid)

    def get_schema(self, attribute_schema_uid: UUID) -> Optional[AttributeSchema]:
        return AttributeSchema.get_by_uid(attribute_schema_uid)

    def get_schemas(self, schema_uid: UUID) -> Sequence[AttributeSchema]:
        return AttributeSchema.get_for_schema(schema_uid)

    def update(self, attribute: Attribute, update: Dict[str, Any]):
        value = update.get("value", None)
        mappable_value = update.get("mappable_value", None)
        if isinstance(attribute.schema, (ObjectAttributeSchema, ListAttributeSchema)):
            raise NotImplementedError(f"Non-implemented update for {attribute.schema}")
        if isinstance(attribute.schema, (ObjectAttributeSchema, ListAttributeSchema)):
            if isinstance(attribute.schema, ObjectAttributeSchema):
                assert isinstance(value, dict)
                sub_attribute_updates = value.values()
            else:
                assert isinstance(value, list)
                sub_attribute_updates = value
            for sub_attribute_update in sub_attribute_updates:
                assert isinstance(sub_attribute_update, dict)
                sub_attribute_uid = sub_attribute_update["uid"]
                sub_attribute = Attribute.get(sub_attribute_uid)
                if sub_attribute is not None:
                    self.update(sub_attribute, sub_attribute_update)
                else:
                    sub_attribute_schema_uid = sub_attribute_update["schema_uid"]
                    sub_attribute_schema = AttributeSchema.get_by_uid(
                        sub_attribute_schema_uid
                    )
                    self.create(sub_attribute_schema, sub_attribute_update)
        else:
            attribute.set_value(value)
            attribute.set_mappable_value(mappable_value)
        return attribute

    def create(self, attribute_schema: AttributeSchema, attribute_data: Dict[str, Any]):
        assert isinstance(attribute_data, dict)
        value = attribute_data.get("value", None)
        mappable_value = attribute_data.get("mappable_value", None)
        if isinstance(attribute_schema, StringAttributeSchema):
            return StringAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, NumericAttributeSchema):
            return NumericAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, MeasurementAttribute):
            assert isinstance(value, Measurement)
            return MeasurementAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, CodeAttributeSchema):
            assert isinstance(value, Code)
            return CodeAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, BooleanAttributeSchema):
            return BooleanAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, ObjectAttributeSchema):
            assert isinstance(value, dict)
            return ObjectAttribute(
                attribute_schema,
                [
                    self._create_sub_attribute(sub_attribute_data)
                    for sub_attribute_data in value.values()
                ],
            )
        if isinstance(attribute_schema, ListAttributeSchema):
            assert isinstance(value, list)
            return ListAttribute(
                attribute_schema,
                [
                    self._create_sub_attribute(sub_attribute_data)
                    for sub_attribute_data in value
                ],
            )
        raise NotImplementedError(f"Non-implemented create for {attribute_schema}")

    def _create_sub_attribute(self, sub_attribute_data: Dict[str, Any]) -> Attribute:
        sub_attribute_schema_uid: UUID = sub_attribute_data["schema_uid"]
        sub_attribute_schema = AttributeSchema.get_by_uid(sub_attribute_schema_uid)
        return self.create(sub_attribute_schema, sub_attribute_data)
