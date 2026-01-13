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

from typing import List, Union

from slidetap.database.attribute import (
    DatabaseAttribute,
    DatabaseBooleanAttribute,
    DatabaseCodeAttribute,
    DatabaseDatetimeAttribute,
    DatabaseEnumAttribute,
    DatabaseListAttribute,
    DatabaseMeasurementAttribute,
    DatabaseNumericAttribute,
    DatabaseObjectAttribute,
    DatabaseStringAttribute,
    DatabaseUnionAttribute,
)
from slidetap.model import (
    Attribute,
    AttributeSchema,
    BooleanAttribute,
    BooleanAttributeSchema,
    CodeAttribute,
    CodeAttributeSchema,
    DatetimeAttribute,
    DatetimeAttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    ListAttribute,
    ListAttributeSchema,
    MeasurementAttribute,
    MeasurementAttributeSchema,
    NumericAttribute,
    NumericAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    StringAttribute,
    StringAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
)


class AttributeValidator:
    @classmethod
    def validate_attribute(
        cls, attribute: Union[Attribute, DatabaseAttribute], schema: AttributeSchema
    ) -> bool:
        if isinstance(
            attribute, (StringAttribute, DatabaseStringAttribute)
        ) and isinstance(schema, StringAttributeSchema):
            return cls._validate_string_attribute(attribute, schema)
        if isinstance(attribute, (EnumAttribute, DatabaseEnumAttribute)) and isinstance(
            schema, EnumAttributeSchema
        ):
            return cls._validate_enum_attribute(attribute, schema)
        if isinstance(
            attribute, (DatetimeAttribute, DatabaseDatetimeAttribute)
        ) and isinstance(schema, DatetimeAttributeSchema):
            return cls._validate_datetime_attribute(attribute, schema)
        if isinstance(
            attribute, (NumericAttribute, DatabaseNumericAttribute)
        ) and isinstance(schema, NumericAttributeSchema):
            return cls._validate_numeric_attribute(attribute, schema)
        if isinstance(
            attribute, (MeasurementAttribute, DatabaseMeasurementAttribute)
        ) and isinstance(schema, MeasurementAttributeSchema):
            return cls._validate_measurement_attribute(attribute, schema)
        if isinstance(attribute, (CodeAttribute, DatabaseCodeAttribute)) and isinstance(
            schema, CodeAttributeSchema
        ):
            return cls._validate_code_attribute(attribute, schema)
        if isinstance(
            attribute, (BooleanAttribute, DatabaseBooleanAttribute)
        ) and isinstance(schema, BooleanAttributeSchema):
            return cls._validate_boolean_attribute(attribute, schema)
        if isinstance(
            attribute, (ObjectAttribute, DatabaseObjectAttribute)
        ) and isinstance(schema, ObjectAttributeSchema):
            return cls._validate_object_attribute(attribute, schema)
        if isinstance(attribute, (ListAttribute, DatabaseListAttribute)) and isinstance(
            schema, ListAttributeSchema
        ):
            return cls._validate_list_attribute(attribute, schema)
        if isinstance(
            attribute, (UnionAttribute, DatabaseUnionAttribute)
        ) and isinstance(schema, UnionAttributeSchema):
            return cls._validate_union_attribute(attribute, schema)
        raise ValueError(
            f"Attribute {attribute, schema} is not a valid attribute type."
        )

    @classmethod
    def _validate_string_attribute(
        cls,
        attribute: Union[StringAttribute, DatabaseStringAttribute],
        schema: StringAttributeSchema,
    ) -> bool:
        attribute.valid = (
            attribute.value is not None and attribute.value != ""
        ) or schema.optional
        return attribute.valid

    @classmethod
    def _validate_enum_attribute(
        cls,
        attribute: Union[EnumAttribute, DatabaseEnumAttribute],
        schema: EnumAttributeSchema,
    ):
        attribute.valid = (
            (
                attribute.value is not None
                and attribute.value != ""
                and attribute.value in schema.allowed_values
            )
            or attribute.value is None
            and schema.optional
        )
        return attribute.valid

    @classmethod
    def _validate_datetime_attribute(
        cls,
        attribute: Union[DatetimeAttribute, DatabaseDatetimeAttribute],
        schema: DatetimeAttributeSchema,
    ):
        attribute.valid = attribute.value is not None or schema.optional
        return attribute.valid

    @classmethod
    def _validate_numeric_attribute(
        cls,
        attribute: Union[NumericAttribute, DatabaseNumericAttribute],
        schema: NumericAttributeSchema,
    ):
        if attribute.value is None:
            valid = schema.optional
        else:
            if schema.min_value is not None and attribute.value < schema.min_value:
                valid = False
            elif schema.max_value is not None and attribute.value > schema.max_value:
                valid = False
            else:
                if schema.is_integer and int(attribute.value) != attribute.value:
                    valid = False
                valid = True
        attribute.valid = valid
        return attribute.valid

    @classmethod
    def _validate_measurement_attribute(
        cls,
        attribute: Union[MeasurementAttribute, DatabaseMeasurementAttribute],
        schema: MeasurementAttributeSchema,
    ):
        if attribute.value is None:
            valid = schema.optional
        else:
            valid_unit = (
                schema.allowed_units is None
                or attribute.value.unit in schema.allowed_units
            )
            valid_value = (
                schema.min_value is None or attribute.value.value >= schema.min_value
            ) and (
                schema.max_value is None or attribute.value.value <= schema.max_value
            )
            valid = valid_unit and valid_value
        attribute.valid = valid
        return attribute.valid

    @classmethod
    def _validate_code_attribute(
        cls,
        attribute: Union[CodeAttribute, DatabaseCodeAttribute],
        schema: CodeAttributeSchema,
    ):
        attribute.valid = (
            attribute.value is not None
            and (
                schema.allowed_schemas is None
                or attribute.value.scheme in schema.allowed_schemas
            )
        ) or (attribute.value is None and schema.optional)
        return attribute.valid

    @classmethod
    def _validate_boolean_attribute(
        cls,
        attribute: Union[BooleanAttribute, DatabaseBooleanAttribute],
        schema: BooleanAttributeSchema,
    ):
        if attribute.value is None:
            valid = schema.optional
        else:
            valid = True
        attribute.valid = valid
        return attribute.valid

    @classmethod
    def _validate_object_attribute(
        cls,
        attribute: Union[ObjectAttribute, DatabaseObjectAttribute],
        schema: ObjectAttributeSchema,
    ):
        if attribute.value is None or len(attribute.value) == 0:
            valid = schema.optional
        else:
            validations: List[bool] = []
            for tag, attribue_schema in schema.attributes.items():
                if tag not in attribute.value:
                    validations.append(attribue_schema.optional)
                else:
                    attribute_validation = cls.validate_attribute(
                        attribute.value[tag], attribue_schema
                    )
                    validations.append(attribute_validation)
            valid = all(validations)
        attribute.valid = valid
        return attribute.valid

    @classmethod
    def _validate_list_attribute(
        cls,
        attribute: Union[ListAttribute, DatabaseListAttribute],
        schema: ListAttributeSchema,
    ):
        if attribute.value is None or len(attribute.value) == 0:
            valid = schema.optional
        else:
            valid_count = (
                schema.min_items is None or len(attribute.value) >= schema.min_items
            ) and (schema.max_items is None or len(attribute.value) <= schema.max_items)
            validations = [
                cls.validate_attribute(value, schema.attribute)
                for value in attribute.value
            ]
            valid = valid_count and all(validations)
        attribute.valid = valid
        return attribute.valid

    @classmethod
    def _validate_union_attribute(
        cls,
        attribute: Union[UnionAttribute, DatabaseUnionAttribute],
        schema: UnionAttributeSchema,
    ):
        if attribute.value is None:
            attribute.valid = schema.optional
        else:
            attribute.valid = cls.validate_attribute(
                attribute.value,
                next(
                    schema
                    for schema in schema.attributes
                    if schema.uid == attribute.value.schema_uid
                ),
            )
        return attribute.valid
