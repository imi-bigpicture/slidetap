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

from typing import Any, Dict
from uuid import UUID

from marshmallow import fields, post_load

from slidetap.database import Item
from slidetap.model import Code, Measurement, ValueStatus
from slidetap.serialization.base import BaseModel
from slidetap.serialization.schema import AttributeSchemaField


class ItemReferenceModel(BaseModel):
    uid = fields.UUID(required=True)
    identifier = fields.String()
    name = fields.String(allow_none=True)
    schema_display_name = fields.String()
    schema_uid = fields.UUID(required=True)

    @post_load
    def load(self, data: Dict[str, Any], **kwargs) -> Item:
        uid = data["uid"]
        if not isinstance(uid, UUID):
            uid = UUID(uid)
        return Item.get(uid)


class MeasurementModel(BaseModel):
    value = fields.Float()
    unit = fields.String()

    @post_load
    def load(self, data: Dict[str, Any], **kwargs) -> Measurement:
        return Measurement(**data)


class CodeModel(BaseModel):
    code = fields.String()
    scheme = fields.String()
    meaning = fields.String()
    scheme_version = fields.String(required=False, allow_none=True)

    @post_load
    def load(self, data: Dict[str, Any], **kwargs) -> Code:
        return Code(
            data["code"],
            data["scheme"],
            data["meaning"],
            data.get("schemeVersion", None),
        )


class AttributeSimplifiedModel(BaseModel):
    uid = fields.UUID()
    schema = AttributeSchemaField()
    mapping_status = fields.Enum(ValueStatus, by_value=True)
    display_value = fields.String()
