from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import Field
from slidetap.model.code import Code
from slidetap.model.external.base import FrozenBaseExternalModel
from slidetap.model.measurement import Measurement

MappingExternalAttributeValueType = TypeVar("MappingExternalAttributeValueType")


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


class MappingItemExternal(
    FrozenBaseExternalModel, Generic[MappingExternalAttributeValueType]
):
    """Base attribute class that all attribute types inherit from."""

    value: MappingExternalAttributeValueType
    display_value: Optional[str] = None


class StringMappingItemExternal(MappingItemExternal[str]):
    """Attribute holding a string value."""

    attribute_value_type: Literal[ExternalAttributeValueType.STRING] = (
        ExternalAttributeValueType.STRING
    )


class EnumMappingItemExternal(MappingItemExternal[str]):
    """Attribute holding an enumerated string value."""

    attribute_value_type: Literal[ExternalAttributeValueType.ENUM] = (
        ExternalAttributeValueType.ENUM
    )


class DatetimeMappingItemExternal(MappingItemExternal[datetime]):
    """Attribute holding a datetime value."""

    attribute_value_type: Literal[ExternalAttributeValueType.DATETIME] = (
        ExternalAttributeValueType.DATETIME
    )


class NumericMappingItemExternal(MappingItemExternal[Union[int, float]]):
    """Attribute holding a numeric value (integer or float)."""

    attribute_value_type: Literal[ExternalAttributeValueType.NUMERIC] = (
        ExternalAttributeValueType.NUMERIC
    )


class MeasurementMappingItemExternal(MappingItemExternal[Measurement]):
    """Attribute holding a measurement value with unit."""

    attribute_value_type: Literal[ExternalAttributeValueType.MEASUREMENT] = (
        ExternalAttributeValueType.MEASUREMENT
    )


class CodeMappingItemExternal(MappingItemExternal[Code]):
    """Attribute holding a coded value with scheme."""

    attribute_value_type: Literal[ExternalAttributeValueType.CODE] = (
        ExternalAttributeValueType.CODE
    )


class BooleanMappingItemExternal(MappingItemExternal[bool]):
    """Attribute holding a boolean value."""

    attribute_value_type: Literal[ExternalAttributeValueType.BOOLEAN] = (
        ExternalAttributeValueType.BOOLEAN
    )


class ObjectMappingItemExternal(
    MappingItemExternal[
        Dict[
            str,
            Annotated[
                Union[
                    StringMappingItemExternal,
                    EnumMappingItemExternal,
                    DatetimeMappingItemExternal,
                    NumericMappingItemExternal,
                    MeasurementMappingItemExternal,
                    CodeMappingItemExternal,
                    BooleanMappingItemExternal,
                    "ObjectMappingItemExternal",
                    "ListMappingItemExternal",
                    "UnionMappingItemExternal",
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


class ListMappingItemExternal(
    MappingItemExternal[
        List[
            Annotated[
                Union[
                    StringMappingItemExternal,
                    EnumMappingItemExternal,
                    DatetimeMappingItemExternal,
                    NumericMappingItemExternal,
                    MeasurementMappingItemExternal,
                    CodeMappingItemExternal,
                    BooleanMappingItemExternal,
                    ObjectMappingItemExternal,
                    "ListMappingItemExternal",
                    "UnionMappingItemExternal",
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


class UnionMappingItemExternal(
    MappingItemExternal[
        Annotated[
            Union[
                StringMappingItemExternal,
                EnumMappingItemExternal,
                DatetimeMappingItemExternal,
                NumericMappingItemExternal,
                MeasurementMappingItemExternal,
                CodeMappingItemExternal,
                BooleanMappingItemExternal,
                ObjectMappingItemExternal,
                ListMappingItemExternal,
                "UnionMappingItemExternal",
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


class MapperExternal(FrozenBaseExternalModel):
    name: str
    attribute_name: str
    root_attribute_name: str


class StringMapperExternal(MapperExternal):
    items: Dict[str, StringMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.STRING] = (
        ExternalAttributeValueType.STRING
    )


class EnumMapperExternal(MapperExternal):
    items: Dict[str, EnumMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.ENUM] = (
        ExternalAttributeValueType.ENUM
    )


class DatetimeMapperExternal(MapperExternal):
    items: Dict[str, DatetimeMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.DATETIME] = (
        ExternalAttributeValueType.DATETIME
    )


class NumericMapperExternal(MapperExternal):
    items: Dict[str, NumericMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.NUMERIC] = (
        ExternalAttributeValueType.NUMERIC
    )


class MeasurementMapperExternal(MapperExternal):
    items: Dict[str, MeasurementMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.MEASUREMENT] = (
        ExternalAttributeValueType.MEASUREMENT
    )


class CodeMapperExternal(MapperExternal):
    items: Dict[str, CodeMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.CODE] = (
        ExternalAttributeValueType.CODE
    )


class BooleanMapperExternal(MapperExternal):
    items: Dict[str, BooleanMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.BOOLEAN] = (
        ExternalAttributeValueType.BOOLEAN
    )


class ObjectMapperExternal(MapperExternal):
    items: Dict[str, ObjectMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.OBJECT] = (
        ExternalAttributeValueType.OBJECT
    )


class ListMapperExternal(MapperExternal):
    items: Dict[str, ListMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.LIST] = (
        ExternalAttributeValueType.LIST
    )


class UnionMapperExternal(MapperExternal):
    items: Dict[str, UnionMappingItemExternal]
    attribute_value_type: Literal[ExternalAttributeValueType.UNION] = (
        ExternalAttributeValueType.UNION
    )


class MapperGroupExternal(FrozenBaseExternalModel):
    name: str
    default_enabled: bool
    mappers: List[
        Annotated[
            Union[
                StringMapperExternal,
                EnumMapperExternal,
                DatetimeMapperExternal,
                NumericMapperExternal,
                MeasurementMapperExternal,
                CodeMapperExternal,
                BooleanMapperExternal,
                ObjectMapperExternal,
                ListMapperExternal,
                UnionMapperExternal,
            ],
            Field(discriminator="attribute_value_type"),
        ]
    ]
