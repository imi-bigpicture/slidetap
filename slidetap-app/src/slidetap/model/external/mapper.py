from typing import Annotated, Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import Field

from slidetap.model.external.attribute import (
    AttributeExternal,
    BooleanAttributeExternal,
    CodeAttributeExternal,
    DatetimeAttributeExternal,
    EnumAttributeExternal,
    ExternalAttributeValueType,
    ListAttributeExternal,
    MeasurementAttributeExternal,
    NumericAttributeExternal,
    ObjectAttributeExternal,
    StringAttributeExternal,
    UnionAttributeExternal,
)
from slidetap.model.external.base import FrozenBaseExternalModel

ItemType = TypeVar("ItemType", bound=AttributeExternal)


class MapperExternal(FrozenBaseExternalModel, Generic[ItemType]):
    name: str
    attribute_name: str
    root_attribute_name: Optional[str] = None
    items: Dict[str, ItemType]


class StringMapperExternal(MapperExternal[StringAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.STRING] = (
        ExternalAttributeValueType.STRING
    )


class EnumMapperExternal(MapperExternal[EnumAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.ENUM] = (
        ExternalAttributeValueType.ENUM
    )


class DatetimeMapperExternal(MapperExternal[DatetimeAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.DATETIME] = (
        ExternalAttributeValueType.DATETIME
    )


class NumericMapperExternal(MapperExternal[NumericAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.NUMERIC] = (
        ExternalAttributeValueType.NUMERIC
    )


class MeasurementMapperExternal(MapperExternal[MeasurementAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.MEASUREMENT] = (
        ExternalAttributeValueType.MEASUREMENT
    )


class CodeMapperExternal(MapperExternal[CodeAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.CODE] = (
        ExternalAttributeValueType.CODE
    )


class BooleanMapperExternal(MapperExternal[BooleanAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.BOOLEAN] = (
        ExternalAttributeValueType.BOOLEAN
    )


class ObjectMapperExternal(MapperExternal[ObjectAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.OBJECT] = (
        ExternalAttributeValueType.OBJECT
    )


class ListMapperExternal(MapperExternal[ListAttributeExternal]):
    attribute_value_type: Literal[ExternalAttributeValueType.LIST] = (
        ExternalAttributeValueType.LIST
    )


class UnionMapperExternal(MapperExternal[UnionAttributeExternal]):
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
