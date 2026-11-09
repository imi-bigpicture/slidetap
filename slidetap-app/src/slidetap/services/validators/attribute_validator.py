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


from collections.abc import Sequence
from datetime import datetime
from typing import Literal

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
    AnyAttribute,
    Attribute,
    AttributeSchema,
    BooleanAttribute,
    BooleanAttributeSchema,
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    DatetimeAttribute,
    DatetimeAttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    ListAttribute,
    ListAttributeSchema,
    Measurement,
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

EntryKey = (
    tuple[Literal["mappable", "text"], str]
    | tuple[Literal["code"], str, str]
    | tuple[Literal["measurement"], float, str]
    | tuple[str, bool | int | float | datetime]
)
"""What an entry of a list is compared by, for a list of unique entries."""


class AttributeValidator:
    @classmethod
    def validate_attribute(
        cls, attribute: Attribute | DatabaseAttribute, schema: AttributeSchema
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
        attribute: StringAttribute | DatabaseStringAttribute,
        schema: StringAttributeSchema,
    ) -> bool:
        attribute.valid = (
            attribute.value is not None and attribute.value != ""
        ) or schema.optional
        return attribute.valid

    @classmethod
    def _validate_enum_attribute(
        cls,
        attribute: EnumAttribute | DatabaseEnumAttribute,
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
        attribute: DatetimeAttribute | DatabaseDatetimeAttribute,
        schema: DatetimeAttributeSchema,
    ):
        attribute.valid = attribute.value is not None or schema.optional
        return attribute.valid

    @classmethod
    def _validate_numeric_attribute(
        cls,
        attribute: NumericAttribute | DatabaseNumericAttribute,
        schema: NumericAttributeSchema,
    ):
        if attribute.value is None:
            valid = schema.optional
        else:
            if (
                schema.min_value is not None
                and attribute.value < schema.min_value
                or schema.max_value is not None
                and attribute.value > schema.max_value
            ):
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
        attribute: MeasurementAttribute | DatabaseMeasurementAttribute,
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
        attribute: CodeAttribute | DatabaseCodeAttribute,
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
        attribute: BooleanAttribute | DatabaseBooleanAttribute,
        schema: BooleanAttributeSchema,
    ):
        valid = schema.optional if attribute.value is None else True
        attribute.valid = valid
        return attribute.valid

    @classmethod
    def _validate_object_attribute(
        cls,
        attribute: ObjectAttribute | DatabaseObjectAttribute,
        schema: ObjectAttributeSchema,
    ):
        if attribute.value is None or len(attribute.value) == 0:
            valid = schema.optional
        else:
            validations: list[bool] = []
            for tag, attribute_schema in schema.attributes.items():
                if tag not in attribute.value:
                    validations.append(attribute_schema.optional)
                else:
                    attribute_validation = cls.validate_attribute(
                        attribute.value[tag], attribute_schema
                    )
                    validations.append(attribute_validation)
            valid = all(validations)
        attribute.valid = valid
        return attribute.valid

    @classmethod
    def _validate_list_attribute(
        cls,
        attribute: ListAttribute | DatabaseListAttribute,
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
            valid = (
                valid_count
                and all(validations)
                and not (schema.unique_items and cls._has_repeats(attribute.value))
            )
        attribute.valid = valid
        return attribute.valid

    @staticmethod
    def _has_repeats(entries: Sequence[AnyAttribute]) -> bool:
        """Whether two of the entries of a list are the same.

        Entries are compared by their effective value, the one they are
        exported with: a code by its scheme and code (not its meaning), text
        trimmed, and a measurement by its value and unit. An entry not yet
        mapped is compared by the text it is mapped from, trimmed, and never
        equals one that is mapped. Entries that are empty, or that hold other
        attributes, are not compared.
        """

        def key(entry: AnyAttribute) -> EntryKey | None:
            value = entry.value
            if value is None:
                mappable = (entry.mappable_value or "").strip()
                return ("mappable", mappable) if mappable else None
            if isinstance(value, Code):
                return ("code", value.scheme, value.code)
            if isinstance(value, Measurement):
                return ("measurement", value.value, value.unit)
            if isinstance(value, str):
                text = value.strip()
                return ("text", text) if text else None
            if isinstance(value, (bool, int, float, datetime)):
                # By type too, as True equals 1 and 1 equals 1.0.
                return (type(value).__name__, value)
            return None

        keys = [found for found in map(key, entries) if found is not None]
        return len(keys) != len(set(keys))

    @classmethod
    def _validate_union_attribute(
        cls,
        attribute: UnionAttribute | DatabaseUnionAttribute,
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
