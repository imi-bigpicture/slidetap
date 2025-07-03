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

"""Schema models for attributes."""

from typing import Annotated, Dict, Literal, Optional, Tuple, TypeVar, Union
from uuid import UUID

from pydantic import Field
from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.datetime_value import DatetimeType

AttributeSchemaType = TypeVar("AttributeSchemaType", bound="AttributeSchema")


class AttributeSchema(FrozenBaseModel):
    """Base schema for all attribute types."""

    uid: UUID
    tag: str
    name: str
    display_name: str
    optional: bool
    read_only: bool
    display_in_table: bool
    attribute_value_type: AttributeValueType


class StringAttributeSchema(AttributeSchema):
    """Schema for string attributes."""

    multiline: bool = False
    attribute_value_type: Literal[AttributeValueType.STRING] = AttributeValueType.STRING


class EnumAttributeSchema(AttributeSchema):
    """Schema for enumerated string attributes."""

    allowed_values: Tuple[str, ...]
    attribute_value_type: Literal[AttributeValueType.ENUM] = AttributeValueType.ENUM


class DatetimeAttributeSchema(AttributeSchema):
    """Schema for datetime attributes."""

    datetime_type: DatetimeType
    attribute_value_type: Literal[AttributeValueType.DATETIME] = (
        AttributeValueType.DATETIME
    )


class NumericAttributeSchema(AttributeSchema):
    """Schema for numeric attributes."""

    is_integer: bool
    attribute_value_type: Literal[AttributeValueType.NUMERIC] = (
        AttributeValueType.NUMERIC
    )


class MeasurementAttributeSchema(AttributeSchema):
    """Schema for measurement attributes with units."""

    allowed_units: Optional[Tuple[str, ...]] = None
    attribute_value_type: Literal[AttributeValueType.MEASUREMENT] = (
        AttributeValueType.MEASUREMENT
    )


class CodeAttributeSchema(AttributeSchema):
    """Schema for coded values with schemas."""

    allowed_schemas: Optional[Tuple[str, ...]] = None
    attribute_value_type: Literal[AttributeValueType.CODE] = AttributeValueType.CODE


class BooleanAttributeSchema(AttributeSchema):
    """Schema for boolean attributes with custom display values."""

    true_display_value: str
    false_display_value: str
    attribute_value_type: Literal[AttributeValueType.BOOLEAN] = (
        AttributeValueType.BOOLEAN
    )


class ObjectAttributeSchema(AttributeSchema):
    """Schema for nested object attributes."""

    display_attributes_in_parent: bool
    display_value_format_string: Optional[str] = None
    attributes: Dict[
        str,
        Annotated[
            Union[
                StringAttributeSchema,
                EnumAttributeSchema,
                DatetimeAttributeSchema,
                NumericAttributeSchema,
                MeasurementAttributeSchema,
                CodeAttributeSchema,
                BooleanAttributeSchema,
                "ObjectAttributeSchema",
                "ListAttributeSchema",
                "UnionAttributeSchema",
            ],
            Field(discriminator="attribute_value_type"),
        ],
    ]
    attribute_value_type: Literal[AttributeValueType.OBJECT] = AttributeValueType.OBJECT


class ListAttributeSchema(AttributeSchema):
    """Schema for list attributes."""

    display_attributes_in_parent: bool
    attribute: Annotated[
        Union[
            StringAttributeSchema,
            EnumAttributeSchema,
            DatetimeAttributeSchema,
            NumericAttributeSchema,
            MeasurementAttributeSchema,
            CodeAttributeSchema,
            BooleanAttributeSchema,
            ObjectAttributeSchema,
            "ListAttributeSchema",
            "UnionAttributeSchema",
        ],
        Field(discriminator="attribute_value_type"),
    ]
    attribute_value_type: Literal[AttributeValueType.LIST] = AttributeValueType.LIST


class UnionAttributeSchema(AttributeSchema):
    """Schema for union attributes that can be one of multiple types."""

    attributes: Tuple[
        Annotated[
            Union[
                StringAttributeSchema,
                EnumAttributeSchema,
                DatetimeAttributeSchema,
                NumericAttributeSchema,
                MeasurementAttributeSchema,
                CodeAttributeSchema,
                BooleanAttributeSchema,
                ObjectAttributeSchema,
                ListAttributeSchema,
                "UnionAttributeSchema",
            ],
            Field(discriminator="attribute_value_type"),
        ],
        ...,
    ]
    attribute_value_type: Literal[AttributeValueType.UNION] = AttributeValueType.UNION


AnyAttributeSchema = Annotated[
    Union[
        StringAttributeSchema,
        EnumAttributeSchema,
        DatetimeAttributeSchema,
        NumericAttributeSchema,
        MeasurementAttributeSchema,
        CodeAttributeSchema,
        BooleanAttributeSchema,
        ObjectAttributeSchema,
        ListAttributeSchema,
        UnionAttributeSchema,
    ],
    Field(discriminator="attribute_value_type"),
]
