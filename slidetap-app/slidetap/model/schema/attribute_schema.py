from abc import ABCMeta
from dataclasses import dataclass
from types import MappingProxyType
from typing import Optional, Tuple, TypeVar
from uuid import UUID

from slidetap.model.datetime_value import DatetimeType

AttributeSchemaType = TypeVar("AttributeSchemaType", bound="AttributeSchema")


@dataclass(frozen=True)
class AttributeSchema(metaclass=ABCMeta):
    uid: UUID
    tag: str
    name: str
    display_name: str
    optional: bool
    read_only: bool
    display_in_table: bool


@dataclass(frozen=True)
class StringAttributeSchema(AttributeSchema):
    pass


@dataclass(frozen=True)
class EnumAttributeSchema(AttributeSchema):
    allowed_values: Tuple[str, ...]


@dataclass(frozen=True)
class DatetimeAttributeSchema(AttributeSchema):
    datetime_type: DatetimeType


@dataclass(frozen=True)
class NumericAttributeSchema(AttributeSchema):
    is_integer: bool


@dataclass(frozen=True)
class MeasurementAttributeSchema(AttributeSchema):
    allowed_units: Optional[Tuple[str, ...]]


@dataclass(frozen=True)
class CodeAttributeSchema(AttributeSchema):
    allowed_schemas: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class BooleanAttributeSchema(AttributeSchema):
    true_display_value: str
    false_display_value: str


@dataclass(frozen=True)
class ObjectAttributeSchema(AttributeSchema):
    display_attributes_in_parent: bool
    display_value_format_string: Optional[str]
    attributes: MappingProxyType[str, AttributeSchema]


@dataclass(frozen=True)
class ListAttributeSchema(AttributeSchema):
    display_attributes_in_parent: bool
    attribute: AttributeSchema


@dataclass(frozen=True)
class UnionAttributeSchema(AttributeSchema):
    attributes: Tuple[AttributeSchema, ...]
