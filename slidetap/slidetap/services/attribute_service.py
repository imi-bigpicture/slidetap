"""Service for accessing attributes."""
from typing import Any, Dict, Optional, Sequence
from uuid import UUID

from slidetap.database import (
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
from slidetap.database.schema.attribute_schema import MeasurementAttributeSchema
from slidetap.model import Code, Measurement


class AttributeService:
    """Attribute service should be used to interface with attributes"""

    def get(self, attribute_uid: UUID) -> Optional[Attribute]:
        attribute = Attribute.get(attribute_uid)
        if attribute is None:
            return None
        return attribute

    def get_for_schema(self, attribute_schema_uid: UUID) -> Sequence[Attribute]:
        return Attribute.get_for_attribute_schema(attribute_schema_uid)

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

    def create(
        self,
        attribute_schema: AttributeSchema,
        attribute_data: Optional[Dict[str, Any]] = None,
    ):
        if attribute_data is not None:
            assert isinstance(attribute_data, dict)
            value = attribute_data.get("value", None)
            mappable_value = attribute_data.get("mappable_value", None)
        else:
            value = None
            mappable_value = None
        if isinstance(attribute_schema, StringAttributeSchema):
            return StringAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, NumericAttributeSchema):
            return NumericAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, MeasurementAttributeSchema):
            assert value is None or isinstance(value, Measurement)
            return MeasurementAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, CodeAttributeSchema):
            assert value is None or isinstance(value, Code)
            return CodeAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, BooleanAttributeSchema):
            return BooleanAttribute(attribute_schema, value, mappable_value)
        if isinstance(attribute_schema, ObjectAttributeSchema):
            if value is not None:
                assert isinstance(value, dict)
                sub_attributes = [
                    self._create_sub_attribute(sub_attribute_data)
                    for sub_attribute_data in value.values()
                ]
            else:
                sub_attributes = [
                    self.create(sub_attribute_schema)
                    for sub_attribute_schema in attribute_schema.attributes
                ]

            return ObjectAttribute(attribute_schema, sub_attributes)
        if isinstance(attribute_schema, ListAttributeSchema):
            if value is not None:
                assert isinstance(value, list)
                sub_attributes = [
                    self._create_sub_attribute(sub_attribute_data)
                    for sub_attribute_data in value
                ]
            else:
                sub_attributes = [
                    self.create(sub_attribute_schema)
                    for sub_attribute_schema in attribute_schema.attributes
                ]
            return ListAttribute(
                attribute_schema,
                sub_attributes,
            )
        raise NotImplementedError(f"Non-implemented create for {attribute_schema}")

    def validate(self, attribute_uid: UUID) -> Optional[bool]:
        attribute = Attribute.get(attribute_uid)
        if attribute is None:
            return None
        return attribute.is_valid

    def _create_sub_attribute(self, sub_attribute_data: Dict[str, Any]) -> Attribute:
        sub_attribute_schema_uid: UUID = sub_attribute_data["schema_uid"]
        sub_attribute_schema = AttributeSchema.get_by_uid(sub_attribute_schema_uid)
        return self.create(sub_attribute_schema, sub_attribute_data)
