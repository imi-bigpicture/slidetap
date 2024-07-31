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

from marshmallow import fields

from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.web.serialization.attribute import AttributeModel
from slidetap.web.serialization.base import BaseModel
from slidetap.web.serialization.common import AttributeSimplifiedModel


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
