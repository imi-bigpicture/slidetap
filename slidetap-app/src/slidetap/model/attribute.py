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

"""Models for attributes that can be assigned to items."""

from datetime import datetime
from typing import (
    Annotated,
    Any,
    Dict,
    Generic,
    Literal,
    Optional,
    Sequence,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.code import Code
from slidetap.model.measurement import Measurement

AttributeType = TypeVar("AttributeType")


class Attribute(CamelCaseBaseModel, Generic[AttributeType]):
    """Base attribute class that all attribute types inherit from."""

    uid: UUID
    schema_uid: UUID
    original_value: Optional[AttributeType] = None
    updated_value: Optional[AttributeType] = None
    mapped_value: Optional[AttributeType] = None
    valid: bool = False
    display_value: Optional[str] = None
    mappable_value: Optional[str] = None
    mapping_item_uid: Optional[UUID] = None
    attribute_value_type: AttributeValueType

    @property
    def value(self) -> Optional[AttributeType]:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value


class StringAttribute(Attribute[str]):
    """Attribute holding a string value."""

    attribute_value_type: Literal[AttributeValueType.STRING] = AttributeValueType.STRING


class EnumAttribute(Attribute[str]):
    """Attribute holding an enumerated string value."""

    attribute_value_type: Literal[AttributeValueType.ENUM] = AttributeValueType.ENUM


class DatetimeAttribute(Attribute[datetime]):
    """Attribute holding a datetime value."""

    attribute_value_type: Literal[AttributeValueType.DATETIME] = (
        AttributeValueType.DATETIME
    )


class NumericAttribute(Attribute[Union[int, float]]):
    """Attribute holding a numeric value (integer or float)."""

    attribute_value_type: Literal[AttributeValueType.NUMERIC] = (
        AttributeValueType.NUMERIC
    )


class MeasurementAttribute(Attribute[Measurement]):
    """Attribute holding a measurement value with unit."""

    attribute_value_type: Literal[AttributeValueType.MEASUREMENT] = (
        AttributeValueType.MEASUREMENT
    )


class CodeAttribute(Attribute[Code]):
    """Attribute holding a coded value with scheme."""

    attribute_value_type: Literal[AttributeValueType.CODE] = AttributeValueType.CODE


class BooleanAttribute(Attribute[bool]):
    """Attribute holding a boolean value."""

    attribute_value_type: Literal[AttributeValueType.BOOLEAN] = (
        AttributeValueType.BOOLEAN
    )


class ObjectAttribute(
    Attribute[
        Dict[
            str,
            Annotated[
                Union[
                    StringAttribute,
                    EnumAttribute,
                    DatetimeAttribute,
                    NumericAttribute,
                    MeasurementAttribute,
                    CodeAttribute,
                    BooleanAttribute,
                    "ObjectAttribute",
                    "ListAttribute",
                    "UnionAttribute",
                ],
                Field(discriminator="attribute_value_type"),
            ],
        ]
    ]
):
    """Attribute holding a dictionary of other attributes."""

    attribute_value_type: Literal[AttributeValueType.OBJECT] = AttributeValueType.OBJECT


class ListAttribute(
    Attribute[
        Sequence[
            Annotated[
                Union[
                    StringAttribute,
                    EnumAttribute,
                    DatetimeAttribute,
                    NumericAttribute,
                    MeasurementAttribute,
                    CodeAttribute,
                    BooleanAttribute,
                    ObjectAttribute,
                    "ListAttribute",
                    "UnionAttribute",
                ],
                Field(discriminator="attribute_value_type"),
            ]
        ]
    ]
):
    """Attribute holding a list of other attributes."""

    attribute_value_type: Literal[AttributeValueType.LIST] = AttributeValueType.LIST


class UnionAttribute(
    Attribute[
        Annotated[
            Union[
                StringAttribute,
                EnumAttribute,
                DatetimeAttribute,
                NumericAttribute,
                MeasurementAttribute,
                CodeAttribute,
                BooleanAttribute,
                ObjectAttribute,
                ListAttribute,
                "UnionAttribute",
            ],
            Field(discriminator="attribute_value_type"),
        ]
    ]
):
    """Attribute that can hold different types of attributes.

    UnionAttribute value is a tuple of a string that defines the schema and an AttributeValue.
    """

    attribute_value_type: Literal[AttributeValueType.UNION] = AttributeValueType.UNION


def attribute_factory(data: Dict[str, Any]) -> Attribute:
    attribute_value_type = AttributeValueType(data.pop("attributeValueType"))
    if attribute_value_type == AttributeValueType.STRING:
        return StringAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.ENUM:
        return EnumAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.DATETIME:
        return DatetimeAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.NUMERIC:
        return NumericAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.MEASUREMENT:
        return MeasurementAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.CODE:
        return CodeAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.BOOLEAN:
        return BooleanAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.OBJECT:
        return ObjectAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.LIST:
        return ListAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.UNION:
        return UnionAttribute.model_validate(data)
    raise ValueError(
        f"Unknown item attribute_value_type: {data.get('attribute_value_type')}"
    ) from None


AnyAttribute = Annotated[
    Union[
        StringAttribute,
        EnumAttribute,
        DatetimeAttribute,
        NumericAttribute,
        MeasurementAttribute,
        CodeAttribute,
        BooleanAttribute,
        ObjectAttribute,
        ListAttribute,
        UnionAttribute,
    ],
    Field(discriminator="attribute_value_type"),
]
