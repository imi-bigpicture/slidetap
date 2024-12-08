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

from typing import Any, Dict, Type

from flask import current_app
from marshmallow import fields, post_dump, post_load
from slidetap.model import AttributeValueType, DatetimeType
from slidetap.model.schema.attribute_schema import (
    AttributeSchema,
    BooleanAttributeSchema,
    CodeAttributeSchema,
    DatetimeAttributeSchema,
    EnumAttributeSchema,
    ListAttributeSchema,
    MeasurementAttributeSchema,
    NumericAttributeSchema,
    ObjectAttributeSchema,
    StringAttributeSchema,
    UnionAttributeSchema,
)
from slidetap.serialization.base import BaseModel


class AttributeSchemaModel(BaseModel):

    def load(self, data: Dict[str, Any], **kwargs) -> AttributeSchema:
        attribute_value_type = AttributeValueType(data["attributeValueType"])
        if attribute_value_type == AttributeValueType.STRING:
            return StringAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.ENUM:
            return EnumAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.DATETIME:
            return DatetimeAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.NUMERIC:
            return NumericAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.MEASUREMENT:
            return MeasurementAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.CODE:
            return CodeAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.BOOLEAN:
            return BooleanAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.OBJECT:
            return ObjectAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.LIST:
            return ListAttributeSchemaModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.UNION:
            return UnionAttributeSchemaModel().load(data)  # type: ignore
        raise ValueError(f"Unknown attribute type {attribute_value_type}.")

    def dump(self, attribute_schema: AttributeSchema, **kwargs):
        if isinstance(attribute_schema, StringAttributeSchema):
            return StringAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, EnumAttributeSchema):
            return EnumAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, DatetimeAttributeSchema):
            return DatetimeAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, NumericAttributeSchema):
            return NumericAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, MeasurementAttributeSchema):
            return MeasurementAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, CodeAttributeSchema):
            return CodeAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, BooleanAttributeSchema):
            return BooleanAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, ObjectAttributeSchema):
            return ObjectAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, ListAttributeSchema):
            return ListAttributeSchemaModel().dump(attribute_schema)
        if isinstance(attribute_schema, UnionAttributeSchema):
            return UnionAttributeSchemaModel().dump(attribute_schema)
        raise ValueError(f"Unknown attribute schema {attribute_schema}.")


class AttributeSchemaDictField(fields.Mapping):
    def _serialize(self, value: Dict[str, AttributeSchema], attr, obj, **kwargs):
        return {key: AttributeSchemaModel().dump(value) for key, value in value.items()}

    def _deserialize(self, value: Dict[str, Any], attr, data, **kwargs):
        return {key: AttributeSchemaModel().load(value) for key, value in value.items()}


class BaseAttributeSchemaModel(BaseModel):
    uid = fields.UUID(required=True)
    tag = fields.String(required=True)
    name = fields.String()
    display_name = fields.String()
    display_in_table = fields.Boolean()
    optional = fields.Boolean()
    read_only = fields.Boolean()

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        raise NotImplementedError()

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> AttributeSchema:
        data.pop("attribute_value_type")
        return self._load_type(**data)


class StringAttributeSchemaModel(BaseAttributeSchemaModel):
    attribute_value_type = fields.Constant(AttributeValueType.STRING.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return StringAttributeSchema


class EnumAttributeSchemaModel(BaseAttributeSchemaModel):
    allowed_values = fields.List(fields.String)
    attribute_value_type = fields.Constant(AttributeValueType.ENUM.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return EnumAttributeSchema


class DatetimeAttributeSchemaModel(BaseAttributeSchemaModel):
    datetime_type = fields.Enum(DatetimeType)
    attribute_value_type = fields.Constant(AttributeValueType.DATETIME.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return DatetimeAttributeSchema


class NumericAttributeSchemaModel(BaseAttributeSchemaModel):
    is_integer = fields.Boolean()
    attribute_value_type = fields.Constant(AttributeValueType.NUMERIC.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return NumericAttributeSchema


class MeasurementAttributeSchemaModel(BaseAttributeSchemaModel):
    allowed_units = fields.List(fields.String, allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.MEASUREMENT.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return MeasurementAttributeSchema


class CodeAttributeSchemaModel(BaseAttributeSchemaModel):
    allowed_codes = fields.List(fields.String, allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.CODE.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return CodeAttributeSchema


class BooleanAttributeSchemaModel(BaseAttributeSchemaModel):
    true_display_value = fields.String(allow_none=True)
    false_display_value = fields.String(allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.BOOLEAN.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return BooleanAttributeSchema


class ObjectAttributeSchemaModel(BaseAttributeSchemaModel):
    display_attributes_in_parent = fields.Boolean()
    display_value_format_string = fields.String()
    attributes = AttributeSchemaDictField()
    attribute_value_type = fields.Constant(AttributeValueType.OBJECT.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return ObjectAttributeSchema


class ListAttributeSchemaModel(BaseAttributeSchemaModel):
    display_attributes_in_parent = fields.Boolean()
    attribute = fields.Nested(AttributeSchemaModel())
    attribute_value_type = fields.Constant(AttributeValueType.LIST.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return ListAttributeSchema


class UnionAttributeSchemaModel(BaseAttributeSchemaModel):
    attributes = AttributeSchemaDictField()
    attribute_value_type = fields.Constant(AttributeValueType.UNION.value)

    @property
    def _load_type(self) -> Type[AttributeSchema]:
        return UnionAttributeSchema
