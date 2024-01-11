from re import U
from typing import Any, Dict, Optional
from uuid import UUID
from flask import current_app

from marshmallow import fields, post_load, validate

from slidetap.database.attribute import (
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
from slidetap.database.schema.attribute_schema import (
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
from slidetap.model import DatetimeType
from slidetap.model.mapping_status import ValueStatus
from slidetap.serialization.base import BaseModel
from slidetap.serialization.common import CodeModel, MeasurementModel
from slidetap.serialization.schema import AttributeSchemaField


class AttributeValueField(fields.Field):
    def _serialize(
        self, value: Any, attr: Optional[str], attribute: Attribute[Any, Any], **kwargs
    ):
        field = self._create_field(attribute.schema)
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
            if attribute_schema.datetime_type == DatetimeType.DATE:
                return fields.Date()
            elif attribute_schema.datetime_type == DatetimeType.DATETIME:
                return fields.DateTime()
            elif attribute_schema.datetime_type == DatetimeType.TIME:
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
        if isinstance(attribute_schema, UnionAttributeSchema):
            return fields.Nested(AttributeModel)
        raise ValueError(f"Unknown attribute schema {attribute_schema}.")


class AttributeModel(BaseModel):
    uid = fields.UUID(required=True, allow_none=True)
    schema = AttributeSchemaField()
    display_value = fields.String()
    mappable_value = fields.String(allow_none=True)
    value = AttributeValueField(allow_none=True)
    mapping_status = fields.Enum(ValueStatus, by_value=True)

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Attribute[Any, Any]:
        uid = data["uid"]
        if uid is not None and not isinstance(uid, UUID):
            uid = UUID(uid)
        value = data["value"]
        attribute = Attribute.get(uid)
        if attribute is not None and attribute.mapping is not None:
            """Only update existing attribute if is for a mapping."""
            current_app.logger.debug(
                f"Updating value of attribute {attribute} to {value}."
            )
            attribute.set_value(value, commit=False)
            return attribute

        schema = data["schema"]
        if isinstance(schema, StringAttributeSchema):
            return StringAttribute(schema, value, commit=False)
        if isinstance(schema, EnumAttributeSchema):
            return EnumAttribute(schema, value, commit=False)
        if isinstance(schema, DatetimeAttributeSchema):
            return DatetimeAttribute(schema, value, commit=False)
        if isinstance(schema, NumericAttributeSchema):
            return NumericAttribute(schema, value, commit=False)
        if isinstance(schema, MeasurementAttributeSchema):
            return MeasurementAttribute(schema, value, commit=False)
        if isinstance(schema, CodeAttributeSchema):
            return CodeAttribute(schema, value, commit=False)
        if isinstance(schema, BooleanAttributeSchema):
            return BooleanAttribute(schema, value, commit=False)
        if isinstance(schema, ObjectAttributeSchema):
            return ObjectAttribute(schema, value, commit=False)
        if isinstance(schema, ListAttributeSchema):
            return ListAttribute(schema, value, commit=False)
        if isinstance(schema, UnionAttributeSchema):
            return UnionAttribute(schema, value, commit=False)
        raise ValueError(f"Unknown attribute schema {schema}.")
