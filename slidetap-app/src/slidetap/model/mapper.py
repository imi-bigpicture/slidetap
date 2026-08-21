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

from typing import TypeVar
from uuid import UUID

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import FrozenBaseModel

MappingAttributeValueType = TypeVar("MappingAttributeValueType")


class MappingItemCreate(FrozenBaseModel):
    mapper_uid: UUID
    expression: str
    attribute: AnyAttribute


class MappingItem(FrozenBaseModel):
    uid: UUID
    mapper_uid: UUID
    expression: str
    attribute: AnyAttribute
    hits: int = 0


class MapperCreate(FrozenBaseModel):
    name: str
    attribute_schema_uid: UUID


class Mapper(FrozenBaseModel):
    uid: UUID
    name: str
    attribute_schema_uid: UUID
    root_attribute_schema_uid: UUID


class MapperGroupCreate(FrozenBaseModel):
    name: str
    default_enabled: bool = False


class MapperGroup(FrozenBaseModel):
    uid: UUID
    name: str
    mappers: list[UUID]
    default_enabled: bool


class UnmappedValue(FrozenBaseModel):
    """A value someone recorded that no mapping accounts for.

    Counted across the items it was found on, so that the wordings worth a key
    can be told from the ones seen once: adding a key for a value seen forty
    times settles forty items at the next remapping.
    """

    attribute_schema_uid: UUID
    display_name: str
    """What the attribute is called, so the list reads without the schema."""
    value: str
    items: int
    mapper_uid: UUID | None
    """The mapper a key would be added to, if the project has one for this.

    None where no mapper covers the attribute at all, which is worth seeing:
    such a value has nowhere to be mapped and nothing else would report it.
    """
