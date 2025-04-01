from dataclasses import dataclass
from typing import List
from uuid import UUID

from slidetap.model.attribute import Attribute


@dataclass
class MappingItem:
    uid: UUID
    mapper_uid: UUID
    expression: str
    attribute: Attribute
    hits: int


@dataclass
class Mapper:
    uid: UUID
    name: str
    attribute_schema_uid: UUID
    root_attribute_schema_uid: UUID
