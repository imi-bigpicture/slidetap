from abc import ABCMeta
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Generic, List, Optional, TypeVar, Union
from uuid import UUID

from slidetap.model.code import Code
from slidetap.model.measurement import Measurement

AttributeType = TypeVar("AttributeType")


@dataclass
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


@dataclass
class StringAttribute(Attribute[str]):
    pass


@dataclass
class EnumAttribute(Attribute[str]):
    pass


@dataclass
class DatetimeAttribute(Attribute[datetime]):
    pass


@dataclass
class NumericAttribute(Attribute[Union[int, float]]):
    pass


@dataclass
class MeasurementAttribute(Attribute[Measurement]):
    pass


@dataclass
class CodeAttribute(Attribute[Code]):
    pass


@dataclass
class BooleanAttribute(Attribute[bool]):
    pass


@dataclass
class ObjectAttribute(Attribute[Dict[str, Attribute]]):
    pass


@dataclass
class ListAttribute(Attribute[List[Attribute]]):
    pass


@dataclass
class UnionAttribute(Attribute[Attribute]):
    """UnionAttribute value is a tuple of a string that defines the schema and an AttributeValue"""

    pass
