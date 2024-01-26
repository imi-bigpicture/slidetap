from marshmallow import fields

from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.base import BaseModel
from slidetap.serialization.common import AttributeSimplifiedModel


class MappingItemModel(BaseModel):
    uid = fields.UUID(required=True, allow_none=True)
    mapper_uid = fields.UUID(required=True)
    expression = fields.String(required=True)
    attribute = fields.Nested(AttributeModel, required=True)


class MappingItemSimplifiedModel(BaseModel):
    uid = fields.UUID(required=True)
    expression = fields.String(required=True)
    attribute = fields.Nested(AttributeSimplifiedModel, required=True)


class MapperModel(BaseModel):
    uid = fields.UUID(required=True, allow_none=True)
    name = fields.String(required=True)
    schema_uid = fields.UUID(required=True)
    attribute_schema_uid = fields.UUID(required=True)
    attribute_schema_name = fields.String()
    attribute_value_type = fields.Enum(AttributeValueType, by_value=True)


class MapperSimplifiedModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    attribute_name = fields.String(required=True)
    attribute_value_type = fields.Enum(AttributeValueType, by_value=True)
