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

"""Service for accessing mappers and mapping items."""

from typing import Iterable, Optional, Sequence, Union
from uuid import UUID

from flask import current_app

from slidetap.database import (
    Attribute,
    AttributeSchema,
    Item,
    Mapper,
    MappingItem,
    Project,
)


class MapperService:
    """Mapper service should be used to interface with mappers."""

    def get_or_create_mapper(
        self,
        name: str,
        attribute_schema: Union[UUID, AttributeSchema],
    ) -> Mapper:
        existing_mapper = Mapper.get_by_name(name)
        if existing_mapper is not None:
            return existing_mapper
        if not isinstance(attribute_schema, AttributeSchema):
            attribute_schema = AttributeSchema.get_by_uid(attribute_schema)
        return Mapper(name, attribute_schema)

    def create_mapper(
        self,
        name: str,
        attribute_schema: Union[UUID, AttributeSchema],
    ) -> Mapper:
        if not isinstance(attribute_schema, AttributeSchema):
            attribute_schema = AttributeSchema.get_by_uid(attribute_schema)
        return Mapper(name, attribute_schema)

    def update_mapper(self, mapper_uid: UUID, name: str) -> Mapper:
        mapper = Mapper.get(mapper_uid)
        mapper.update_name(name)
        return mapper

    def delete_mapper(self, mapper_uid: UUID) -> None:
        mapper = Mapper.get(mapper_uid)
        mapper.delete()

    def get_all_mappers(self) -> Iterable[Mapper]:
        return Mapper.get_all()

    def get_mapper(self, mapper_uid) -> Mapper:
        return Mapper.get(mapper_uid)

    def get_or_create_mapping(
        self, mapper_uid: UUID, expression: str, attribute: Attribute
    ) -> MappingItem:
        mapper = Mapper.get(mapper_uid)
        existing_mapping = mapper.get_mapping(expression)
        if existing_mapping is not None:
            return existing_mapping
        mapping = mapper.add(expression, attribute)
        mappable_attributes = mapper.get_mappable_attributes(True)
        for mappable_attribute in mappable_attributes:
            self.map(mappable_attribute, validate_parent_item=True)
        return mapping

    def create_mapping(
        self, mapper_uid: UUID, expression: str, attribute: Attribute
    ) -> MappingItem:
        mapper = Mapper.get(mapper_uid)
        mapping = mapper.add(expression, attribute)
        mappable_attributes = mapper.get_mappable_attributes(True)
        for mappable_attribute in mappable_attributes:
            self.map(mappable_attribute, validate_parent_item=True)
        return mapping

    def update_mapping(
        self, mapping_uid: UUID, expression: str, attribute: Attribute
    ) -> MappingItem:
        mapping = self.get_mapping(mapping_uid)
        mapping.update(expression, attribute)
        mapper = self.get_mapper(mapping.mapper_uid)
        for mapped_attribute in mapper.get_mappable_attributes():
            self.map(mapped_attribute, validate_parent_item=True)
        return mapping

    def delete_mapping(self, mapping_uid: UUID):
        mapping = self.get_mapping(mapping_uid)
        mapping.delete()

    def get_mapping(self, mapping_uid: UUID) -> MappingItem:
        return MappingItem.get_by_uid(mapping_uid)

    def get_mappings(self, mapper_uid: UUID) -> Sequence[MappingItem]:
        mapper = Mapper.get(mapper_uid)
        return mapper.mappings

    @classmethod
    def get_mapping_for_attribute(cls, attribute: Attribute) -> Optional[MappingItem]:
        if attribute.mappable_value is None:
            return None
        mapper = Mapper.get_for_attribute(attribute)
        if mapper is None:
            return None
        return mapper.get_mapping_for_value(attribute.mappable_value)

    def apply_to_project(self, project: Union[UUID, Project]):
        items = Item.get_for_project(project)
        for item in items:
            self.apply_mappers_to_item(item)

    def apply_mappers_to_item(self, item: Item):
        attributes_to_map = item.recursive_recursive_get_all_mappable_attributes()
        if len(attributes_to_map) == 0:
            return
        current_app.logger.debug(
            f"Applying mappers to item {item} {item.name} {item.identifier}"
        )
        for attribute in attributes_to_map:
            self.map(attribute, validate_parent_item=False)
        item.validate(relations=False)

    @classmethod
    def map(
        cls,
        attribute: Attribute,
        commit: bool = True,
        validate_parent_item: bool = True,
    ) -> Optional[MappingItem]:
        if attribute.mappable_value is None:
            return
        mapping = cls.get_mapping_for_attribute(attribute)
        if mapping is None:
            attribute.clear_mapping(commit)
            return
        attribute.set_mapping(mapping)
        if validate_parent_item:
            cls._validate_parent_item(attribute)
        return mapping

    @classmethod
    def _validate_parent_item(cls, mapped_attribute: Attribute):
        if mapped_attribute.item_uid is not None:
            item = Item.get(mapped_attribute.item_uid)
            item.validate(relations=False)
