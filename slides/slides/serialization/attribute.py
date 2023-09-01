from typing import Any, Dict, Optional
from uuid import UUID

from marshmallow import fields, validate

from slides.database.attribute import Attribute
from slides.database.schema.attribute_schema import (
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
)
from slides.model import DatetimeValueType
from slides.serialization.base import BaseModel
from slides.serialization.common import CodeModel, MeasurementModel
from slides.serialization.schema import AttributeSchemaField


class AttributeValueField(fields.Field):
    def _serialize(
        self, value: Any, attr: Optional[str], attribute: Attribute, **kwargs
    ):
        field = self.field = self._create_field(attribute.schema)
        return field._serialize(value, attr, attribute, **kwargs)

    def _deserialize(
        self,
        value: Any,
        attr: Optional[str],
        attribute_data: Optional[Dict[str, Any]],
        **kwargs,
    ):
        assert attribute_data is not None
        schema_uid = UUID(attribute_data["schema"]["uid"])
        schema = AttributeSchema.get_by_uid(schema_uid)
        assert schema is not None
        field = self._create_field(schema)
        return field._deserialize(value, attr, attribute_data, **kwargs)

    def _create_field(self, attribute_schema: AttributeSchema) -> fields.Field:
        if isinstance(attribute_schema, StringAttributeSchema):
            return fields.String()
        if isinstance(attribute_schema, EnumAttributeSchema):
            if attribute_schema.allowed_values is not None:
                validator = validate.OneOf(attribute_schema.allowed_values)
            else:
                validator = None
            return fields.String(validate=validator)
        if isinstance(attribute_schema, DatetimeAttributeSchema):
            # TODO Not sure if we should serialze to Date or Time, as the value
            # in the database is always a datetime
            if attribute_schema.datetime_type == DatetimeValueType.DATE:
                return fields.Date()
            elif attribute_schema.datetime_type == DatetimeValueType.DATETIME:
                return fields.DateTime()
            elif attribute_schema.datetime_type == DatetimeValueType.TIME:
                return fields.Time()
            raise ValueError(f"Unknown datatime type {attribute_schema.datetime_type}.")
        if isinstance(attribute_schema, NumericAttributeSchema):
            if attribute_schema.is_int:
                return fields.Integer()
            return fields.Float()
        if isinstance(attribute_schema, MeasurementAttributeSchema):
            return fields.Nested(MeasurementModel())
        if isinstance(attribute_schema, CodeAttributeSchema):
            return fields.Nested(CodeModel())
        if isinstance(attribute_schema, BooleanAttributeSchema):
            return fields.Boolean()
        if isinstance(attribute_schema, ObjectAttributeSchema):
            return fields.Dict(keys=fields.String, values=fields.Nested(AttributeModel))
        if isinstance(attribute_schema, ListAttributeSchema):
            return fields.List(fields.Nested(AttributeModel))
        raise ValueError(f"Unknown attribute schema {attribute_schema}.")


class AttributeModel(BaseModel):
    schema = AttributeSchemaField()
    display_value = fields.String(dump_only=True)
    uid = fields.UUID(required=True, allow_none=True)
    mappable_value = fields.String(allow_none=True)
    value = AttributeValueField()
