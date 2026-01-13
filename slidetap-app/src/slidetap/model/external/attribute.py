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

from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import Field

from slidetap.model.code import Code
from slidetap.model.external.base import FrozenBaseExternalModel
from slidetap.model.measurement import Measurement

AttributeExternalValueType = TypeVar("AttributeExternalValueType")


class ExternalAttributeValueType(str, Enum):
    STRING = "string"
    DATETIME = "datetime"
    NUMERIC = "numeric"
    MEASUREMENT = "measurement"
    CODE = "code"
    ENUM = "enum"
    BOOLEAN = "boolean"
    OBJECT = "object"
    LIST = "list"
    UNION = "union"


class AttributeExternal(FrozenBaseExternalModel, Generic[AttributeExternalValueType]):
    """Base attribute class that all attribute types inherit from."""

    value: AttributeExternalValueType
    display_value: Optional[str] = None


class StringAttributeExternal(AttributeExternal[str]):
    """Attribute holding a string value."""

    attribute_value_type: Literal[ExternalAttributeValueType.STRING] = (
        ExternalAttributeValueType.STRING
    )


class EnumAttributeExternal(AttributeExternal[str]):
    """Attribute holding an enumerated string value."""

    attribute_value_type: Literal[ExternalAttributeValueType.ENUM] = (
        ExternalAttributeValueType.ENUM
    )


class DatetimeAttributeExternal(AttributeExternal[datetime]):
    """Attribute holding a datetime value."""

    attribute_value_type: Literal[ExternalAttributeValueType.DATETIME] = (
        ExternalAttributeValueType.DATETIME
    )


class NumericAttributeExternal(AttributeExternal[Union[int, float]]):
    """Attribute holding a numeric value (integer or float)."""

    attribute_value_type: Literal[ExternalAttributeValueType.NUMERIC] = (
        ExternalAttributeValueType.NUMERIC
    )


class MeasurementAttributeExternal(AttributeExternal[Measurement]):
    """Attribute holding a measurement value with unit."""

    attribute_value_type: Literal[ExternalAttributeValueType.MEASUREMENT] = (
        ExternalAttributeValueType.MEASUREMENT
    )


class CodeAttributeExternal(AttributeExternal[Code]):
    """Attribute holding a coded value with scheme."""

    attribute_value_type: Literal[ExternalAttributeValueType.CODE] = (
        ExternalAttributeValueType.CODE
    )


class BooleanAttributeExternal(AttributeExternal[bool]):
    """Attribute holding a boolean value."""

    attribute_value_type: Literal[ExternalAttributeValueType.BOOLEAN] = (
        ExternalAttributeValueType.BOOLEAN
    )


class ObjectAttributeExternal(
    AttributeExternal[
        Dict[
            str,
            Annotated[
                Union[
                    StringAttributeExternal,
                    EnumAttributeExternal,
                    DatetimeAttributeExternal,
                    NumericAttributeExternal,
                    MeasurementAttributeExternal,
                    CodeAttributeExternal,
                    BooleanAttributeExternal,
                    "ObjectAttributeExternal",
                    "ListAttributeExternal",
                    "UnionAttributeExternal",
                ],
                Field(discriminator="attribute_value_type"),
            ],
        ]
    ]
):
    """Attribute holding a dictionary of other attributes."""

    attribute_value_type: Literal[ExternalAttributeValueType.OBJECT] = (
        ExternalAttributeValueType.OBJECT
    )


class ListAttributeExternal(
    AttributeExternal[
        List[
            Annotated[
                Union[
                    StringAttributeExternal,
                    EnumAttributeExternal,
                    DatetimeAttributeExternal,
                    NumericAttributeExternal,
                    MeasurementAttributeExternal,
                    CodeAttributeExternal,
                    BooleanAttributeExternal,
                    ObjectAttributeExternal,
                    "ListAttributeExternal",
                    "UnionAttributeExternal",
                ],
                Field(discriminator="attribute_value_type"),
            ]
        ]
    ]
):
    """Attribute holding a list of other attributes."""

    attribute_value_type: Literal[ExternalAttributeValueType.LIST] = (
        ExternalAttributeValueType.LIST
    )


class UnionAttributeExternal(
    AttributeExternal[
        Annotated[
            Union[
                StringAttributeExternal,
                EnumAttributeExternal,
                DatetimeAttributeExternal,
                NumericAttributeExternal,
                MeasurementAttributeExternal,
                CodeAttributeExternal,
                BooleanAttributeExternal,
                ObjectAttributeExternal,
                ListAttributeExternal,
                "UnionAttributeExternal",
            ],
            Field(discriminator="attribute_value_type"),
        ]
    ]
):
    """Attribute that can hold different types of attributes.

    UnionAttribute value is a tuple of a string that defines the schema and an AttributeValue.
    """

    attribute_name: str
    attribute_value_type: Literal[ExternalAttributeValueType.UNION] = (
        ExternalAttributeValueType.UNION
    )
