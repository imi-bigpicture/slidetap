from typing import Any, Dict, Optional
from marshmallow import fields

from slidetap.database.schema import (
    AttributeSchema,
    ObjectAttributeSchema,
)
from slidetap.database.schema.attribute_schema import (
    BooleanAttributeSchema,
    CodeAttributeSchema,
    DatetimeAttributeSchema,
    EnumAttributeSchema,
    ListAttributeSchema,
    MeasurementAttributeSchema,
    StringAttributeSchema,
    UnionAttributeSchema,
    NumericAttributeSchema,
)
from slidetap.database.schema.item_schema import ItemValueType
from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.datetime_value_type import DatetimeType
from slidetap.serialization.base import BaseModel


class AttributeSchemaOneOfModel(BaseModel):
    def dump(self, attribute_schema: AttributeSchema, **kwargs):
        if isinstance(attribute_schema, StringAttributeSchema):
            return StringAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, DatetimeAttributeSchema):
            return DatetimeAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, NumericAttributeSchema):
            return NumericAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, MeasurementAttributeSchema):
            return MeasurementAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, CodeAttributeSchema):
            return CodeAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, BooleanAttributeSchema):
            return BooleanAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, ObjectAttributeSchema):
            return ObjectAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, ListAttributeSchema):
            return ListAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, UnionAttributeSchema):
            return UnionAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, EnumAttributeSchema):
            return EnumAttributeSchemaModel().dump(attribute_schema, **kwargs)
        raise ValueError(f"Unknown schema {attribute_schema}.")

    def load(self, data: Dict[str, Any], **kwargs):
        return AttributeSchemaModel().load(data, **kwargs)


class AttributeSchemaField(fields.Field):
    def _serialize(
        self, value: AttributeSchema, attr: Optional[str], obj: Any, **kwargs
    ):
        model = self._create_model(value)
        return model.dump(value)
        return fields.Nested(model)._serialize(value, attr, obj, **kwargs)

    def _deserialize(
        self, value: Any, attr: Optional[str], data: Optional[Dict[str, Any]], **kwargs
    ):
        return AttributeSchemaModel().load(value)
        return fields.Nested(AttributeSchemaModel)._deserialize(
            value, attr, data, **kwargs
        )

    def _create_model(self, attribute_schema: AttributeSchema):
        if isinstance(attribute_schema, StringAttributeSchema):
            return StringAttributeSchemaModel()
        if isinstance(attribute_schema, DatetimeAttributeSchema):
            return DatetimeAttributeSchemaModel()
        if isinstance(attribute_schema, NumericAttributeSchema):
            return NumericAttributeSchemaModel()
        if isinstance(attribute_schema, MeasurementAttributeSchema):
            return MeasurementAttributeSchemaModel()
        if isinstance(attribute_schema, CodeAttributeSchema):
            return CodeAttributeSchemaModel()
        if isinstance(attribute_schema, BooleanAttributeSchema):
            return BooleanAttributeSchemaModel()
        if isinstance(attribute_schema, ObjectAttributeSchema):
            return ObjectAttributeSchemaModel()
        if isinstance(attribute_schema, ListAttributeSchema):
            return ListAttributeSchemaModel()
        if isinstance(attribute_schema, EnumAttributeSchema):
            return EnumAttributeSchemaModel()
        if isinstance(attribute_schema, UnionAttributeSchema):
            return UnionAttributeSchemaModel()
        raise ValueError(f"Unknown schema {attribute_schema.name}.")


class AttributeSchemaModel(BaseModel):
    uid = fields.UUID(required=True)
    tag = fields.String(dump_only=True)
    display_name = fields.String(dump_only=True)
    attribute_value_type = fields.Enum(
        AttributeValueType, by_value=True, dump_only=True
    )


class StringAttributeSchemaModel(BaseModel):
    pass


class EnumAttributeSchemaModel(AttributeSchemaModel):
    allowed_values = fields.List(fields.String, allow_none=True, dump_only=True)


class DatetimeAttributeSchemaModel(AttributeSchemaModel):
    datetime_type = fields.Enum(DatetimeType, by_value=True, dump_only=True)


class NumericAttributeSchemaModel(AttributeSchemaModel):
    is_int = fields.Boolean(dump_only=True)


class MeasurementAttributeSchemaModel(AttributeSchemaModel):
    allowed_units = fields.List(fields.String, allow_none=True, dump_only=True)


class CodeAttributeSchemaModel(AttributeSchemaModel):
    allowed_schemas = fields.List(fields.String, allow_none=True, dump_only=True)


class BooleanAttributeSchemaModel(AttributeSchemaModel):
    true_display_value = fields.String(allow_none=True, dump_only=True)
    false_display_value = fields.String(allow_none=True, dump_only=True)


class ObjectAttributeSchemaModel(AttributeSchemaModel):
    display_attributes_in_parent = fields.Boolean(dump_only=True)
    attributes = fields.List(AttributeSchemaField(), dump_only=True)


class ListAttributeSchemaModel(AttributeSchemaModel):
    display_attributes_in_parent = fields.Boolean(dump_only=True)
    attribute = fields.Nested(AttributeSchemaOneOfModel, dump_only=True)


class UnionAttributeSchemaModel(AttributeSchemaModel):
    attributes = fields.List(AttributeSchemaField(), dump_only=True)


class ItemSchemaModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True, dump_only=True)
    display_name = fields.String(required=True, dump_only=True)
    item_value_type = fields.Enum(ItemValueType, by_value=True, dump_only=True)
    attributes = fields.List(fields.Nested(AttributeSchemaModel), dump_only=True)
    schema_uid = fields.UUID(required=True)
    parents = fields.List(fields.Nested("ItemSchemaModel"), dump_only=True)
