from typing import List
from uuid import UUID

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import FrozenBaseModel


class MappingItem(FrozenBaseModel):
    uid: UUID
    mapper_uid: UUID
    expression: str
    attribute: AnyAttribute
    hits: int = 0


class Mapper(FrozenBaseModel):
    uid: UUID
    name: str
    attribute_schema_uid: UUID
    root_attribute_schema_uid: UUID


class MapperGroup(FrozenBaseModel):
    uid: UUID
    name: str
    mappers: List[UUID]
    default_enabled: bool
