from typing import Any, Dict, Optional
from uuid import UUID
from marshmallow import fields, post_load

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
from slidetap.database.schema.item_schema import ItemSchema, ItemValueType
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

    def _deserialize(
        self, value: Any, attr: Optional[str], data: Optional[Dict[str, Any]], **kwargs
    ):
        uid = UUID(hex=value["uid"])
        attribute_schema = AttributeSchema.get_by_uid(uid)
        return attribute_schema
        model = self._create_model_from_value_type(
            AttributeValueType(value["attributeValueType"])
        )
        return model.load(value)

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

    def _create_model_from_value_type(self, attribute_value_type: AttributeValueType):
        if attribute_value_type == AttributeValueType.STRING:
            return StringAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.DATETIME:
            return DatetimeAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.NUMERIC:
            return NumericAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.MEASUREMENT:
            return MeasurementAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.CODE:
            return CodeAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.BOOLEAN:
            return BooleanAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.OBJECT:
            return ObjectAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.LIST:
            return ListAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.ENUM:
            return EnumAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.UNION:
            return UnionAttributeSchemaModel()
        raise ValueError(f"Unknown schema {attribute_value_type}.")


class AttributeSchemaModel(BaseModel):
    uid = fields.UUID(required=True)
    tag = fields.String()
    display_name = fields.String()
    attribute_value_type = fields.Enum(AttributeValueType, by_value=True)
    display_in_table = fields.Boolean()
    schema_uid = fields.UUID(required=True)

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return AttributeSchema.get_by_uid(uid)


class StringAttributeSchemaModel(AttributeSchemaModel):
    pass


class EnumAttributeSchemaModel(AttributeSchemaModel):
    allowed_values = fields.List(fields.String, allow_none=True)


class DatetimeAttributeSchemaModel(AttributeSchemaModel):
    datetime_type = fields.Enum(DatetimeType, by_value=True)


class NumericAttributeSchemaModel(AttributeSchemaModel):
    is_int = fields.Boolean()


class MeasurementAttributeSchemaModel(AttributeSchemaModel):
    allowed_units = fields.List(fields.String, allow_none=True)


class CodeAttributeSchemaModel(AttributeSchemaModel):
    allowed_schemas = fields.List(
        fields.String,
        allow_none=True,
    )


class BooleanAttributeSchemaModel(AttributeSchemaModel):
    true_display_value = fields.String()
    false_display_value = fields.String()


class ObjectAttributeSchemaModel(AttributeSchemaModel):
    display_attributes_in_parent = fields.Boolean()
    attributes = fields.List(AttributeSchemaField())


class ListAttributeSchemaModel(AttributeSchemaModel):
    display_attributes_in_parent = fields.Boolean()
    attribute = fields.Nested(AttributeSchemaOneOfModel)


class UnionAttributeSchemaModel(AttributeSchemaModel):
    attributes = fields.List(AttributeSchemaField())


class BaseItemSchemaModel(BaseModel):
    """Base without children and parents to avoid circular dependencies."""

    uid = fields.UUID(required=True)
    name = fields.String(
        required=True,
    )
    display_name = fields.String(
        required=True,
    )
    item_value_type = fields.Enum(
        ItemValueType,
        by_value=True,
    )
    attributes = fields.List(fields.Nested(AttributeSchemaModel))
    schema_uid = fields.UUID(required=True)

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return ItemSchema.get_by_uid(uid)


class ItemSchemaModel(BaseItemSchemaModel):
    children = fields.List(fields.Nested(BaseItemSchemaModel))
    parents = fields.List(fields.Nested(BaseItemSchemaModel))

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return ItemSchema.get_by_uid(uid)
