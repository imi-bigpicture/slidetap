from abc import ABCMeta
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Generic, Optional, Tuple, TypeVar, Union
from uuid import UUID

from slidetap.model.code import Code
from slidetap.model.measurement import Measurement

AttributeType = TypeVar("AttributeType")


@dataclass(frozen=True)
class Attribute(Generic[AttributeType], metaclass=ABCMeta):
    uid: UUID
    schema_uid: UUID
    original_value: Optional[AttributeType] = None
    updated_value: Optional[AttributeType] = None
    mapped_value: Optional[AttributeType] = None
    valid: bool = False
    display_value: Optional[str] = None
    mappable_value: Optional[str] = None
    mapping_item_uid: Optional[UUID] = None

    @property
    def value(self) -> Optional[AttributeType]:
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value


@dataclass(frozen=True)
class StringAttribute(Attribute[str]):
    pass


@dataclass(frozen=True)
class EnumAttribute(Attribute[str]):
    pass


@dataclass(frozen=True)
class DatetimeAttribute(Attribute[datetime]):
    pass


@dataclass(frozen=True)
class NumericAttribute(Attribute[Union[int, float]]):
    pass


@dataclass(frozen=True)
class MeasurementAttribute(Attribute[Measurement]):
    pass


@dataclass(frozen=True)
class CodeAttribute(Attribute[Code]):
    pass


@dataclass(frozen=True)
class BooleanAttribute(Attribute[bool]):
    pass


@dataclass(frozen=True)
class ObjectAttribute(Attribute[MappingProxyType[str, Attribute]]):
    pass


@dataclass(frozen=True)
class ListAttribute(Attribute[Tuple[Attribute, ...]]):
    pass


@dataclass(frozen=True)
class UnionAttribute(Attribute[Attribute]):
    """UnionAttribute value is a tuple of a string that defines the schema and an AttributeValue"""

    pass
