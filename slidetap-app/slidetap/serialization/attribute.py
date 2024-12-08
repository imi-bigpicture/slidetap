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

from marshmallow import fields, post_load

from slidetap.model import ValueStatus
from slidetap.model.attribute import (
    Attribute,
    BooleanAttribute,
    CodeAttribute,
    DatetimeAttribute,
    EnumAttribute,
    ListAttribute,
    MeasurementAttribute,
    NumericAttribute,
    ObjectAttribute,
    StringAttribute,
    UnionAttribute,
)
from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.serialization.base import BaseModel
from slidetap.serialization.common import CodeModel, MeasurementModel


class AttributeModel(BaseModel):
    def load(self, data: Dict[str, Any], **kwargs) -> Attribute:
        attribute_value_type = AttributeValueType(data["attributeValueType"])
        if attribute_value_type == AttributeValueType.STRING:
            return StringAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.ENUM:
            return EnumAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.DATETIME:
            return DatetimeAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.NUMERIC:
            return NumericAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.MEASUREMENT:
            return MeasurementAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.CODE:
            return CodeAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.BOOLEAN:
            return BooleanAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.OBJECT:
            return ObjectAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.LIST:
            return ListAttributeModel().load(data)  # type: ignore
        if attribute_value_type == AttributeValueType.UNION:
            return UnionAttributeModel().load(data)  # type: ignore
        raise ValueError(f"Unknown attribute type {attribute_value_type}.")

    def dump(self, attribute: Attribute, **kwargs) -> Dict[str, Any]:
        if isinstance(attribute, StringAttribute):
            return StringAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, EnumAttribute):
            return EnumAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, DatetimeAttribute):
            return DatetimeAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, NumericAttribute):
            return NumericAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, MeasurementAttribute):
            return MeasurementAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, CodeAttribute):
            return CodeAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, BooleanAttribute):
            return BooleanAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, ObjectAttribute):
            return ObjectAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, ListAttribute):
            return ListAttributeModel().dump(attribute)  # type: ignore
        if isinstance(attribute, UnionAttribute):
            return UnionAttributeModel().dump(attribute)  # type: ignore
        raise ValueError(f"Unknown attribute {attribute}.")


class AttributeDictField(fields.Dict):
    def _serialize(self, value: Dict[str, Attribute], attr, obj, **kwargs):
        return {key: AttributeModel().dump(value) for key, value in value.items()}

    def _deserialize(self, value: Dict[str, Any], attr, data, **kwargs):
        return {key: AttributeModel().load(value) for key, value in value.items()}


class BaseAttributeModel(BaseModel):
    uid = fields.UUID(allow_none=True)
    schema_uid = fields.UUID(allow_none=True)
    display_value = fields.String(allow_none=True)
    mappable_value = fields.String(allow_none=True)
    mapping_status = fields.Enum(ValueStatus, by_value=True)
    valid = fields.Boolean()
    mapping_item_uid = fields.UUID(allow_none=True)

    @property
    def _load_type(self) -> Type[Attribute]:
        raise NotImplementedError()

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Attribute:
        data.pop("attribute_value_type")
        return self._load_type(**data)


class StringAttributeModel(BaseAttributeModel):
    original_value = fields.String(allow_none=True)
    updated_value = fields.String(allow_none=True)
    mapped_value = fields.String(allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.STRING.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return StringAttribute


class EnumAttributeModel(BaseAttributeModel):
    original_value = fields.String(allow_none=True)
    updated_value = fields.String(allow_none=True)
    mapped_value = fields.String(allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.ENUM.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return EnumAttribute


class DatetimeAttributeModel(BaseAttributeModel):
    original_value = fields.DateTime(allow_none=True)
    updated_value = fields.DateTime(allow_none=True)
    mapped_value = fields.DateTime(allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.DATETIME.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return DatetimeAttribute


class NumericAttributeModel(BaseAttributeModel):
    original_value = fields.Float(allow_none=True)
    updated_value = fields.Float(allow_none=True)
    mapped_value = fields.Float(allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.NUMERIC.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return NumericAttribute


class MeasurementAttributeModel(BaseAttributeModel):
    original_value = fields.Nested(MeasurementModel, allow_none=True)
    updated_value = fields.Nested(MeasurementModel, allow_none=True)
    mapped_value = fields.Nested(MeasurementModel, allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.MEASUREMENT.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return MeasurementAttribute


class CodeAttributeModel(BaseAttributeModel):
    original_value = fields.Nested(CodeModel, allow_none=True)
    updated_value = fields.Nested(CodeModel, allow_none=True)
    mapped_value = fields.Nested(CodeModel, allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.CODE.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return CodeAttribute


class BooleanAttributeModel(BaseAttributeModel):
    original_value = fields.Boolean(allow_none=True)
    updated_value = fields.Boolean(allow_none=True)
    mapped_value = fields.Boolean(allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.BOOLEAN.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return BooleanAttribute


class ObjectAttributeModel(BaseAttributeModel):
    original_value = fields.Dict(
        keys=fields.String, values=fields.Nested(AttributeModel()), allow_none=True
    )
    updated_value = fields.Dict(
        keys=fields.String, values=fields.Nested(AttributeModel()), allow_none=True
    )
    mapped_value = fields.Dict(
        keys=fields.String, values=fields.Nested(AttributeModel()), allow_none=True
    )
    attribute_value_type = fields.Constant(AttributeValueType.OBJECT.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return ObjectAttribute


class ListAttributeModel(BaseAttributeModel):
    original_value = fields.List(fields.Nested(AttributeModel()), allow_none=True)
    updated_value = fields.List(fields.Nested(AttributeModel()), allow_none=True)
    mapped_value = fields.List(fields.Nested(AttributeModel()), allow_none=True)
    attribute_value_type = fields.Constant(AttributeValueType.LIST.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return ListAttribute


class UnionAttributeModel(BaseAttributeModel):
    original_value = fields.Tuple(
        (fields.String(), fields.Nested(AttributeModel())), allow_none=True
    )
    updated_value = fields.Tuple(
        (fields.String(), fields.Nested(AttributeModel())), allow_none=True
    )
    mapped_value = fields.Tuple(
        (fields.String(), fields.Nested(AttributeModel())), allow_none=True
    )
    attribute_value_type = fields.Constant(AttributeValueType.UNION.value)

    @property
    def _load_type(self) -> Type[Attribute]:
        return UnionAttribute
