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

import logging
import re
from functools import lru_cache
from re import Pattern
from typing import Dict, Iterable, Optional, Sequence, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseListAttribute,
    DatabaseMapper,
    DatabaseMappingItem,
    DatabaseObjectAttribute,
    DatabaseUnionAttribute,
)
from slidetap.model import (
    Attribute,
    AttributeSchema,
    ListAttribute,
    Mapper,
    MapperGroup,
    MappingItem,
    ObjectAttribute,
)
from slidetap.model.attribute import AnyAttribute
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

    def get_all_mapper_groups(
        self, session: Optional[Session] = None
    ) -> Sequence[MapperGroup]:
        with self._database_service.get_session(session) as session:
            groups = self._database_service.get_mapper_groups(session)
            return [group.model for group in groups]

    def get_or_create_mapper_group(
        self,
        name: str,
        default_enabled: bool,
        session: Optional[Session] = None,
    ) -> MapperGroup:
        with self._database_service.get_session(session) as session:
            existing_group = self._database_service.get_mapper_group_by_name(
                session, name
            )
            if existing_group is not None:
                return existing_group.model
            group = self._database_service.add_mapper_group(
                session, name, default_enabled
            )
            return group.model

    def add_mappers_to_group(
        self,
        group: MapperGroup,
        mappers: Iterable[Mapper],
        session: Optional[Session] = None,
    ) -> MapperGroup:
        with self._database_service.get_session(session) as session:
            existing_group = self._database_service.get_mapper_group(session, group.uid)
            if existing_group is None:
                raise ValueError(f"Mapper group {group.uid} does not exist.")
            for mapper in mappers:
                logging.debug(f"Adding mapper {mapper.uid} to group {group.uid}")
                database_mapper = self._database_service.get_mapper(session, mapper.uid)
                if database_mapper not in existing_group.mappers:
                    existing_group.mappers.append(database_mapper)
            return existing_group.model

    def get_or_create_mapper(
        self,
        name: str,
        attribute_schema: Union[UUID, AttributeSchema],
        root_attribute_schema: Optional[Union[UUID, AttributeSchema]] = None,
        session: Optional[Session] = None,
    ) -> Mapper:
        with self._database_service.get_session(session) as session:
            existing_mapper = self._database_service.get_mapper_by_name(session, name)
            if existing_mapper is not None:
                return existing_mapper.model
            mapper = self._create_mapper(
                session, name, attribute_schema, root_attribute_schema
            )
            return mapper.model

    def get_or_create_mapping(
        self,
        mapper_uid: UUID,
        expression: str,
        attribute: Attribute,
        apply: bool = False,
        session: Optional[Session] = None,
    ) -> MappingItem:
        with self._database_service.get_session(session) as session:
            existing_mapping = (
                self._database_service.get_optional_mapping_for_expression(
                    session, mapper_uid, expression
                )
            )
            if existing_mapping is not None:
                return existing_mapping.model

            mapping = self._database_service.add_mapping(
                session, mapper_uid, expression, attribute
            )
            if apply:
                self._apply_mapping_item_to_all_attributes(session, mapper_uid, mapping)
            return mapping.model

    def get_mappers(self) -> Iterable[Mapper]:
        with self._database_service.get_session() as session:
            mappers = session.scalars(select(DatabaseMapper))
            return [mapper.model for mapper in mappers]

    def get_mapper(self, mapper_uid) -> Mapper:
        with self._database_service.get_session() as session:
            return self._database_service.get_mapper(session, mapper_uid).model

    def get_mapping(self, mapping_uid: UUID) -> MappingItem:
        with self._database_service.get_session() as session:
            return self._database_service.get_mapping(session, mapping_uid).model

    def get_mappings_for_mapper(self, mapper_uid: UUID) -> Sequence[MappingItem]:
        with self._database_service.get_session() as session:
            mappings = self._database_service.get_mappings_for_mapper(
                session, mapper_uid
            )
            return [mapping.model for mapping in mappings]

    def get_mapping_for_attribute(self, attribute: Attribute) -> Optional[MappingItem]:
        pass

    def create_mapper(self, mapper: Mapper) -> Mapper:
        with self._database_service.get_session() as session:
            return self._create_mapper(
                session,
                mapper.name,
                mapper.attribute_schema_uid,
                mapper.root_attribute_schema_uid,
            ).model

    def create_mapping(self, mapping: MappingItem) -> MappingItem:
        with self._database_service.get_session() as session:
            database_mapping = self._database_service.add_mapping(
                session, mapping.mapper_uid, mapping.expression, mapping.attribute
            )
            self._apply_mapping_item_to_all_attributes(
                session, mapping.mapper_uid, database_mapping
            )
            return database_mapping.model

    def update_mapper(self, mapper: Mapper) -> Mapper:
        with self._database_service.get_session() as session:
            database_mapper = self._database_service.get_mapper(session, mapper.uid)
            database_mapper.name = mapper.name
            return database_mapper.model

    def update_mapping(self, mapping: MappingItem) -> MappingItem:
        with self._database_service.get_session() as session:
            database_mapping = self._database_service.get_mapping(session, mapping.uid)
            database_mapping.update(mapping.expression, mapping.attribute)
            self._apply_mapping_item_to_all_attributes(
                session, mapping.mapper_uid, database_mapping
            )
            return database_mapping.model

    def delete_mapper(self, mapper_uid: UUID) -> None:
        with self._database_service.get_session() as session:
            mapper = self._database_service.get_mapper(session, mapper_uid)
            session.delete(mapper)

    def delete_mapping(self, mapping_uid: UUID):
        with self._database_service.get_session() as session:
            mapping = self.get_mapping(mapping_uid)
            session.delete(mapping)

    def apply_mappers_to_attributes(
        self,
        attributes: Dict[str, DatabaseAttribute],
        project_mappers: Iterable[Union[Mapper, DatabaseMapper, UUID]],
        validate: bool = True,
        session: Optional[Session] = None,
    ):
        with self._database_service.get_session(session) as session:
            self._apply_mappers_to_attributes(
                attributes, project_mappers, validate, session
            )

    def apply_mapper_to_unmapped_attributes(
        self, mapper: Mapper, session: Optional[Session] = None
    ):
        with self._database_service.get_session(session) as session:
            mappable_attributes = self._get_mappable_attributes_for_mapper(
                mapper, session
            )
            for attribute in mappable_attributes:
                logging.debug(
                    f"Trying to map attribute {attribute.uid} with value {attribute.mappable_value}"
                )
                assert attribute.mappable_value is not None
                mapping = self._get_mapping_in_mapper_for_value(
                    mapper, attribute.mappable_value, session
                )
                if mapping is not None:
                    logging.debug(
                        f"Attribute {attribute.uid} with value {attribute.mappable_value} is now mapped."
                    )
                    attribute.set_mapping(mapping)
                else:
                    logging.debug(
                        f"Attribute {attribute.uid} with value {attribute.mappable_value} is still not mapped."
                    )

    def _apply_mappers_to_attributes(
        self,
        attributes: Dict[str, DatabaseAttribute],
        mappers_to_use: Iterable[Union[Mapper, DatabaseMapper, UUID]],
        validate: bool,
        session: Session,
    ):

        for attribute in attributes.values():
            mappers = self._database_service.get_mappers_for_root_attribute(
                session,
                attribute.schema_uid,
                [
                    mapper if isinstance(mapper, UUID) else mapper.uid
                    for mapper in mappers_to_use
                ],
            )
            # TODO this does not work if a mapping updates the root attribute and
            # another updates a child attribute. The root attribute update will be but into
            # the mapped_value and child attributes in the original_value.
            for mapper in mappers:
                logging.debug(
                    f"Applying mapper {mapper.name} to root attribute {attribute.tag}"
                )
                attributes[attribute.tag] = self._apply_mapper_to_root_attribute(
                    session, mapper, attribute, validate=validate
                )
        return attributes

    def _get_mapping_in_mapper_for_value(
        self, mapper: Mapper, value: str, session: Session
    ) -> Optional[DatabaseMappingItem]:
        for expression in self._database_service.get_mapper_expressions(
            session, mapper.uid
        ):
            if re.match(expression, value) is not None:
                return self._get_mapping_for_expression_in_mapper(
                    mapper, expression, session
                )
        return None

    def _get_mapping_for_expression_in_mapper(
        self, mapper: Mapper, expression: str, session: Session
    ) -> DatabaseMappingItem:
        return self._database_service.get_mapping_for_expression(
            session, mapper.uid, expression
        )

    def _create_mapper(
        self,
        session: Session,
        name: str,
        attribute_schema: Union[UUID, AttributeSchema],
        root_attribute_schema: Optional[Union[UUID, AttributeSchema]] = None,
    ) -> DatabaseMapper:
        if isinstance(attribute_schema, AttributeSchema):
            attribute_schema = attribute_schema.uid
        if isinstance(root_attribute_schema, AttributeSchema):
            root_attribute_schema = root_attribute_schema.uid
        if root_attribute_schema is None:
            root_attribute_schema = attribute_schema
        return self._database_service.add_mapper(
            session,
            name,
            attribute_schema_uid=attribute_schema,
            root_attribute_schema_uid=root_attribute_schema,
        )

    def _get_mappable_attributes_for_mapper(
        self, mapper: Mapper, session: Session
    ) -> Iterable[DatabaseAttribute]:
        query = select(DatabaseAttribute).filter(
            DatabaseAttribute.schema_uid == mapper.root_attribute_schema_uid,
        )
        return session.scalars(query)

    def _apply_mapping_item_to_all_attributes(
        self,
        session: Session,
        mapper_uid: UUID,
        mapping: DatabaseMappingItem,
        validate: bool = True,
    ):
        mapper = self._database_service.get_mapper(session, mapper_uid)
        root_attributes = self._database_service.get_attributes_for_schema(
            session, mapper.root_attribute_schema_uid
        )
        for root_attribute in root_attributes:
            self._apply_mapper_to_root_attribute(
                session, mapper, root_attribute, mapping.expression, validate
            )

    def _get_matching_expression(
        self,
        session: Session,
        mapper: DatabaseMapper,
        attribute: Union[Attribute, DatabaseAttribute],
        expression: Optional[str] = None,
    ):
        if expression is not None:
            expressions = [expression]
        else:
            expressions = self._database_service.get_mapper_expressions(
                session, mapper.uid
            )
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
        session: Session,
        mapper: DatabaseMapper,
        attribute: DatabaseAttribute,
        expression: Optional[str] = None,
        validate: bool = True,
    ):
        if mapper.root_attribute_schema_uid == mapper.attribute_schema_uid:
            matching_expression = self._get_matching_expression(
                session, mapper, attribute, expression
            )
            if matching_expression is not None:
                mapping = self._database_service.get_mapping_for_expression(
                    session, mapper.uid, matching_expression
                )
                attribute.set_mapping(mapping.attribute.original_value)
                attribute.mapping_item_uid = mapping.uid
                mapping.increment_hits()
        elif (
            isinstance(attribute, DatabaseListAttribute)
            and attribute.original_value is not None
        ):
            logging.debug(f"Applying mapper {mapper} to list attribute {attribute.tag}")
            mapped_value = [
                self._recursive_mapping(session, mapper, item)
                for item in attribute.original_value
            ]
            attribute.set_original_value(mapped_value)
        elif (
            isinstance(attribute, DatabaseUnionAttribute)
            and attribute.original_value is not None
        ):
            logging.debug(
                f"Applying mapper {mapper} to union attribute {attribute.tag}"
            )
            mapped_value = self._recursive_mapping(
                session, mapper, attribute.original_value
            )
            attribute.set_original_value(mapped_value)
        elif (
            isinstance(attribute, DatabaseObjectAttribute)
            and attribute.original_value is not None
        ):
            logging.debug(
                f"Applying mapper {mapper} to object attribute {attribute.tag}"
            )

            mapped_value = {
                tag: self._recursive_mapping(session, mapper, item)
                for tag, item in attribute.original_value.items()
            }
            attribute.set_original_value(mapped_value)
        if validate:
            self._validation_service.validate_attribute(attribute, session)
        return attribute

    def _recursive_mapping(
        self,
        session: Session,
        mapper: DatabaseMapper,
        attribute: AnyAttribute,
        expression: Optional[str] = None,
    ) -> AnyAttribute:
        if attribute.schema_uid == mapper.attribute_schema_uid:
            matching_expression = self._get_matching_expression(
                session, mapper, attribute, expression
            )
            if matching_expression is not None:
                mapping = self._database_service.get_mapping_for_expression(
                    session, mapper.uid, matching_expression
                )
                logging.debug(
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
                self._recursive_mapping(session, mapper, child_attribute)
            return attribute
        elif (
            isinstance(attribute, ObjectAttribute)
            and attribute.original_value is not None
        ):
            for tag, child_attribute in attribute.original_value.items():
                self._recursive_mapping(session, mapper, child_attribute)
            return attribute
        return attribute
