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

import re
from functools import lru_cache
from re import Pattern
from typing import Iterable, Optional, Sequence, Union
from uuid import UUID

from flask import current_app

from slidetap.database import (
    DatabaseAttribute,
    DatabaseItem,
    DatabaseListAttribute,
    DatabaseObjectAttribute,
    DatabaseProject,
    DatabaseUnionAttribute,
    Mapper,
    MappingItem,
    db,
)
from slidetap.model import (
    Attribute,
    AttributeSchema,
    Item,
    ListAttribute,
    ObjectAttribute,
    Project,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.validation_service import ValidationService


class MapperService:
    """Mapper service should be used to interface with mappers."""

    def __init__(
        self, validation_service: ValidationService, database_service: DatabaseService
    ):
        self._validation_service = validation_service
        self._database_service = database_service

    @lru_cache(1000)
    def create_pattern(self, pattern: str) -> Pattern:
        return re.compile(pattern)

    def get_or_create_mapper(
        self,
        name: str,
        attribute_schema: Union[UUID, AttributeSchema],
        root_attribute_schema: Optional[Union[UUID, AttributeSchema]] = None,
    ) -> Mapper:
        existing_mapper = Mapper.get_by_name(name)
        if existing_mapper is not None:
            return existing_mapper
        return self.create_mapper(name, attribute_schema, root_attribute_schema)

    def create_mapper(
        self,
        name: str,
        attribute_schema: Union[UUID, AttributeSchema],
        root_attribute_schema: Optional[Union[UUID, AttributeSchema]] = None,
    ) -> Mapper:
        if isinstance(attribute_schema, AttributeSchema):
            attribute_schema = attribute_schema.uid
        if isinstance(root_attribute_schema, AttributeSchema):
            root_attribute_schema = root_attribute_schema.uid
        if root_attribute_schema is None:
            root_attribute_schema = attribute_schema
        return Mapper(
            name,
            attribute_schema_uid=attribute_schema,
            root_attribute_schema_uid=root_attribute_schema,
        )

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
        existing_mapping = mapper.get_optional_mapping(expression)
        if existing_mapping is not None:
            return existing_mapping
        mapping = mapper.add(expression, attribute)
        self._apply_mapping_item_to_all_attributes(mapper, mapping)
        return mapping

    def create_mapping(
        self, mapper_uid: UUID, expression: str, attribute: Attribute
    ) -> MappingItem:
        mapper = Mapper.get(mapper_uid)
        mapping = mapper.add(expression, attribute)
        self._apply_mapping_item_to_all_attributes(mapper, mapping)
        return mapping

    def update_mapping(
        self, mapping_uid: UUID, expression: str, attribute: Attribute
    ) -> MappingItem:
        mapping = self.get_mapping(mapping_uid)
        mapping.update(expression, attribute)
        mapper = self.get_mapper(mapping.mapper_uid)
        self._apply_mapping_item_to_all_attributes(mapper, mapping)
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
        # TODO implement update
        return None
        # if attribute.mappable_value is None:
        #     return None
        # mappers = Mapper.get_for_attribute(attribute)
        # if mapper is None:
        #     return None
        # return mapper.get_mapping_for_value(attribute.mappable_value)

    def apply_to_project(self, project: Union[UUID, Project, DatabaseProject]):
        items = self._database_service.get_project_items(project)
        for item in items:
            current_app.logger.debug(f"Applying mappers to item {item.uid}")
            self.apply_mappers_to_item(item)

    def apply_mappers_to_item(
        self, item: Union[UUID, Item, DatabaseItem], commit: bool = True
    ):
        if isinstance(item, UUID):
            item = DatabaseItem.get(item)
        elif isinstance(item, Item):
            item = DatabaseItem.get(item.uid)
        for tag in item.attribute_tags:
            attribute = item.get_attribute(tag)
            current_app.logger.debug(f"Applying mappers to attribute {attribute.tag}")
            mappers = Mapper.get_for_root_attribute(attribute)
            # TODO this does not work if a mapping updates the root attribute and
            # another updates a child attribute. The root attribute update will be but into
            # the mapped_value and child attributes in the original_value.
            for mapper in mappers:
                self._apply_mapper_to_root_attribute(mapper, attribute)
        current_app.logger.debug(f"Commiting mapping changes to item {item.uid}")
        if commit:
            db.session.commit()

    def apply_mappers_to_attribute(
        self, attribute: Union[UUID, Attribute, DatabaseAttribute]
    ):
        if isinstance(attribute, UUID):
            attribute = DatabaseAttribute.get(attribute)
        elif isinstance(attribute, Attribute):
            attribute = DatabaseAttribute.get(attribute.uid)
        mappers = Mapper.get_for_root_attribute(attribute)
        for mapper in mappers:
            self._apply_mapper_to_root_attribute(mapper, attribute)
        db.session.commit()

    def _apply_mapping_item_to_all_attributes(
        self, mapper: Mapper, mapping: MappingItem
    ):
        root_attributes = DatabaseAttribute.get_for_attribute_schema(
            mapper.root_attribute_schema_uid
        )
        for root_attribute in root_attributes:
            self._apply_mapper_to_root_attribute(
                mapper, root_attribute, mapping.expression
            )

    def _get_matching_expression(
        self,
        mapper: Mapper,
        attribute: Union[Attribute, DatabaseAttribute],
        expression: Optional[str] = None,
    ):
        if expression is not None:
            expressions = [expression]
        else:
            expressions = mapper.expressions
        return next(
            (
                expression
                for expression in expressions
                if self.create_pattern(expression).match(attribute.mappable_value)
            ),
            None,
        )

    def _apply_mapper_to_root_attribute(
        self,
        mapper: Mapper,
        attribute: DatabaseAttribute,
        expression: Optional[str] = None,
    ):
        if mapper.root_attribute_schema_uid == mapper.attribute_schema_uid:
            matching_expression = self._get_matching_expression(
                mapper, attribute, expression
            )
            if matching_expression is not None:
                mapping = mapper.get_mapping(matching_expression)
                attribute.set_mapping(mapping.attribute.original_value)
                attribute.mapping_item_uid = mapping.uid
                mapping.increment_hits()
        elif (
            isinstance(attribute, DatabaseListAttribute)
            and attribute.original_value is not None
        ):
            current_app.logger.debug(
                f"Applying mapper {mapper} to list attribute {attribute.tag}"
            )
            mapped_value = [
                self._recursive_mapping(mapper, item)
                for item in attribute.original_value
            ]
            attribute.set_original_value(mapped_value)
        elif (
            isinstance(attribute, DatabaseUnionAttribute)
            and attribute.original_value is not None
        ):
            current_app.logger.debug(
                f"Applying mapper {mapper} to union attribute {attribute.tag}"
            )
            mapped_value = self._recursive_mapping(mapper, attribute.original_value)
            attribute.set_original_value(mapped_value)
        elif (
            isinstance(attribute, DatabaseObjectAttribute)
            and attribute.original_value is not None
        ):
            current_app.logger.debug(
                f"Applying mapper {mapper} to object attribute {attribute.tag}"
            )

            mapped_value = {
                tag: self._recursive_mapping(mapper, item)
                for tag, item in attribute.original_value.items()
            }
            attribute.set_original_value(mapped_value)
        self._validation_service.validate_attribute(attribute)

    def _recursive_mapping(
        self, mapper: Mapper, attribute: Attribute, expression: Optional[str] = None
    ) -> Attribute:
        current_app.logger.debug(
            f"Recursively applying mapper {mapper} to attribute {attribute.uid} with mappable value {attribute.mappable_value}"
            f"Attribute schema {attribute.schema_uid} mapper attribute schema {mapper.attribute_schema_uid}"
        )
        if attribute.schema_uid == mapper.attribute_schema_uid:
            matching_expression = self._get_matching_expression(
                mapper, attribute, expression
            )
            if matching_expression is not None:
                mapping = mapper.get_mapping(matching_expression)
                current_app.logger.debug(
                    f"Applying mapping {matching_expression} with value {mapping.attribute.original_value} to attribute {attribute.uid}"
                )
                mapping.increment_hits()
                attribute.mapped_value = mapping.attribute.original_value
                attribute.mapping_item_uid = mapping.uid
                attribute.display_value = mapping.attribute.display_value
                return attribute
        elif (
            isinstance(attribute, ListAttribute)
            and attribute.original_value is not None
        ):
            for child_attribute in attribute.original_value:
                self._recursive_mapping(mapper, child_attribute)
            return attribute
        elif (
            isinstance(attribute, ObjectAttribute)
            and attribute.original_value is not None
        ):
            for tag, child_attribute in attribute.original_value.items():
                self._recursive_mapping(mapper, child_attribute)
            return attribute
        return attribute
