from typing import Any, Dict

from marshmallow import fields, post_load

from slidetap.model import Code, MappingStatus, Measurement
from slidetap.serialization.base import BaseModel
from slidetap.serialization.schema import AttributeSchemaField


class ItemReferenceModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(dump_only=True)
    schema_display_name = fields.String(dump_only=True)
    schema_uid = fields.UUID(required=True)


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
    mapping_status = fields.Enum(MappingStatus, by_value=True)
    display_value = fields.String()
