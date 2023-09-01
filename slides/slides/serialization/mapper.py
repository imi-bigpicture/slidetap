from marshmallow import fields
from slides.model.attribute_value_type import AttributeValueType
from slides.serialization.base import BaseModel
from slides.serialization.attribute import AttributeModel


class MappingItemModel(BaseModel):
    uid = fields.UUID(required=True, allow_none=True)
    expression = fields.String(required=True)
    attribute = fields.Nested(AttributeModel, required=True)


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


class MappingModel(BaseModel):
    attribute_uid = fields.UUID()
    mappable_value = fields.String()
    mapper_name = fields.String()
    mapper_uid = fields.UUID()
    expression = fields.String()
    value = fields.Nested(AttributeModel())
