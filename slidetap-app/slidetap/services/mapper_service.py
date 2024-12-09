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

import dataclasses
from typing import Iterable, Optional, Sequence, Union
from uuid import UUID

from flask import current_app

from slidetap.database import (
    DatabaseItem,
    DatabaseProject,
    Mapper,
    MappingItem,
    db,
)
from slidetap.database.attribute import (
    DatabaseAttribute,
    DatabaseListAttribute,
    DatabaseObjectAttribute,
    DatabaseUnionAttribute,
)
from slidetap.model.attribute import Attribute, ListAttribute, ObjectAttribute
from slidetap.model.item import Item
from slidetap.model.project import Project
from slidetap.model.schema.attribute_schema import AttributeSchema
from slidetap.services.validation_service import ValidationService


class MapperService:
    """Mapper service should be used to interface with mappers."""

    def __init__(self, validation_service: ValidationService):
        self._validation_service = validation_service

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
        existing_mapping = mapper.get_mapping(expression)
        if existing_mapping is not None:
            return existing_mapping
        mapping = mapper.add(expression, attribute)
        self._apply_mapping_items_to_all_attributes(mapper, mapping)
        return mapping

    def create_mapping(
        self, mapper_uid: UUID, expression: str, attribute: Attribute
    ) -> MappingItem:
        mapper = Mapper.get(mapper_uid)
        mapping = mapper.add(expression, attribute)
        self._apply_mapping_items_to_all_attributes(mapper, mapping)
        return mapping

    def update_mapping(
        self, mapping_uid: UUID, expression: str, attribute: Attribute
    ) -> MappingItem:
        mapping = self.get_mapping(mapping_uid)
        mapping.update(expression, attribute)
        mapper = self.get_mapper(mapping.mapper_uid)
        self._apply_mapping_items_to_all_attributes(mapper, mapping)
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
        if isinstance(project, UUID):
            project = DatabaseProject.get(project)
        elif isinstance(project, Project):
            project = DatabaseProject.get(project.uid)
        items = DatabaseItem.get_for_project(project)
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
        for attribute in item.attributes.values():
            current_app.logger.debug(f"Applying mappers to attribute {attribute.tag}")
            mappers = Mapper.get_for_root_attribute(attribute)
            # TODO this does not work if a mapping updates the root attribute and
            # another updates a child attribute. The root attribute update will be but into
            # the mapped_value and child attributes in the origina_value.
            for mapper in mappers:
                for mapping in mapper.mappings:
                    current_app.logger.debug(
                        f"Applying mapping {mapping.expression} to attribute {attribute.tag}"
                    )
                    self._apply_mapping_item_to_root_attribute(
                        mapper, mapping, attribute
                    )
        current_app.logger.debug(f"Commiting mapping changes to item {item.uid}")
        self._validation_service.validate_attributes_for_item(item)
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
            for mapping in mapper.mappings:
                self._apply_mapping_item_to_root_attribute(mapper, mapping, attribute)
        db.session.commit()

    def _apply_mapping_items_to_all_attributes(
        self, mapper: Mapper, mapping: MappingItem
    ):
        root_attributes = DatabaseAttribute.get_for_attribute_schema(
            mapper.root_attribute_schema_uid
        )
        for root_attribute in root_attributes:
            self._apply_mapping_item_to_root_attribute(mapper, mapping, root_attribute)

    def _apply_mapping_item_to_root_attribute(
        self, mapper: Mapper, mapping: MappingItem, attribute: DatabaseAttribute
    ):
        if (
            mapper.root_attribute_schema_uid == mapper.attribute_schema_uid
            and mapping.matches(attribute.mappable_value)
        ):
            current_app.logger.debug(
                f"Applying mapping {mapping.expression} to root attribute {attribute.tag}"
            )
            attribute.set_mapping(mapping.attribute.original_value)
            attribute.mapping_item_uid = mapping.uid
        elif (
            isinstance(attribute, DatabaseListAttribute)
            and attribute.original_value is not None
        ):
            current_app.logger.debug(
                f"Applying mapping {mapping.expression} to list attribute {attribute.tag}"
            )
            mapped_value = [
                self._recursive_mapping(mapper, mapping, item)
                for item in attribute.original_value
            ]
            attribute.set_original_value(mapped_value)
        elif (
            isinstance(attribute, DatabaseUnionAttribute)
            and attribute.original_value is not None
        ):
            current_app.logger.debug(
                f"Applying mapping {mapping.expression} to union attribute {attribute.tag}"
            )

            mapped_value = self._recursive_mapping(
                mapper, mapping, attribute.original_value
            )
            attribute.set_original_value(mapped_value)
        elif (
            isinstance(attribute, DatabaseObjectAttribute)
            and attribute.original_value is not None
        ):
            current_app.logger.debug(
                f"Applying mapping {mapping.expression} to object attribute {attribute.tag}"
            )

            mapped_value = {
                tag: self._recursive_mapping(mapper, mapping, item)
                for tag, item in attribute.original_value.items()
            }
            attribute.set_original_value(mapped_value)
        self._validation_service.validate_attribute(attribute)

    @classmethod
    def _recursive_mapping(
        cls, mapper: Mapper, mapping: MappingItem, attribute: Attribute
    ) -> Attribute:
        current_app.logger.debug(
            f"Recursively applying mapping {mapping.expression} to attribute {attribute.uid} with mappable value {attribute.mappable_value}"
            f"Attribute schema {attribute.schema_uid} mapper attribute schema {mapper.attribute_schema_uid}"
        )
        if attribute.schema_uid == mapper.attribute_schema_uid and mapping.matches(
            attribute.mappable_value
        ):
            current_app.logger.debug(
                f"Applying mapping {mapping.expression} with value {mapping.attribute.original_value} to attribute {attribute.uid}"
            )
            return dataclasses.replace(
                attribute,
                mapped_value=mapping.attribute.original_value,
                display_value=mapping.attribute.display_value,
                mapping_item_uid=mapping.uid,
            )
        elif (
            isinstance(attribute, ListAttribute)
            and attribute.original_value is not None
        ):
            return dataclasses.replace(
                attribute,
                original_value=[
                    cls._recursive_mapping(mapper, mapping, item)
                    for item in attribute.original_value
                ],
            )
        elif (
            isinstance(attribute, ObjectAttribute)
            and attribute.original_value is not None
        ):
            return dataclasses.replace(
                attribute,
                original_value={
                    tag: cls._recursive_mapping(mapper, mapping, item)
                    for tag, item in attribute.original_value.items()
                },
            )
        return attribute
