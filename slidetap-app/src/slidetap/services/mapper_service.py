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
from typing import Iterable, Optional, Sequence, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseMapper,
    DatabaseMappingItem,
    NotAllowedActionError,
)
from slidetap.database.item import DatabaseItem
from slidetap.external_interfaces import MapperInjectorInterface
from slidetap.model import (
    Attribute,
    AttributeSchema,
    BatchStatus,
    ListAttribute,
    Mapper,
    MapperGroup,
    MappingItem,
    ObjectAttribute,
)
from slidetap.model.attribute import AnyAttribute, UnionAttribute
from slidetap.model.mapper import MapperCreate, MappingItemCreate
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class MapperService:
    """Mapper service should be used to interface with mappers."""

    _STABLE_BATCH_STATUSES = frozenset(
        {
            BatchStatus.METADATA_SEARCH_COMPLETE,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
            BatchStatus.IMAGE_POST_PROCESSING_COMPLETE,
        }
    )

    def __init__(
        self,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        schema_service: SchemaService,
        database_service: DatabaseService,
        mapper_injector: Optional[MapperInjectorInterface] = None,
    ):
        self._attribute_service = attribute_service
        self._validation_service = validation_service
        self._schema_service = schema_service
        self._database_service = database_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if mapper_injector is not None:
            self._inject(mapper_injector)

    def _inject(self, mapper_injector: MapperInjectorInterface) -> None:
        with self._database_service.get_session() as session:
            for group, mappers in mapper_injector.inject():
                group = self.get_or_create_mapper_group(
                    group.name, group.default_enabled, session=session
                )
                group_mappers = []
                for mapper, items in mappers:
                    mapper = self.get_or_create_mapper(
                        mapper.name,
                        mapper.attribute_schema_uid,
                        mapper.root_attribute_schema_uid,
                        session=session,
                    )
                    group_mappers.append(mapper)
                    for item in items:
                        self.get_or_create_mapping(
                            mapper.uid,
                            item.expression,
                            item.attribute,
                            session=session,
                        )
                session.flush()
                self.add_mappers_to_group(group, group_mappers, session=session)

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
            database_group = self._database_service.get_mapper_group(session, group.uid)
            for mapper in mappers:
                self._logger.debug(f"Adding mapper {mapper.uid} to group {group.uid}")
                database_mapper = self._database_service.get_mapper(session, mapper.uid)
                if database_mapper not in database_group.mappers:
                    database_group.mappers.add(database_mapper)
            return database_group.model

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
            self._set_display_value(attribute)
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

    def create_mapper(self, mapper: MapperCreate) -> Mapper:
        with self._database_service.get_session() as session:
            return self._create_mapper(
                session,
                mapper.name,
                mapper.attribute_schema_uid,
                mapper.attribute_schema_uid,
            ).model

    def create_mapping(self, mapping: MappingItemCreate) -> MappingItem:
        with self._database_service.get_session() as session:
            database_mapping = self._database_service.add_mapping(
                session, mapping.mapper_uid, mapping.expression, mapping.attribute  # type: ignore
            )
            session.flush()
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
        attributes: Iterable[AnyAttribute],
        project_mappers: Iterable[Union[Mapper, DatabaseMapper, UUID]],
        validate: bool = True,
        session: Optional[Session] = None,
    ) -> Iterable[AnyAttribute]:
        with self._database_service.get_session(session) as session:
            yield from self._apply_mappers_to_attributes(
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
                self._logger.debug(
                    f"Trying to map attribute {attribute.uid} with value {attribute.mappable_value}"
                )
                if attribute.mappable_value is None:
                    raise ValueError(
                        f"Attribute {attribute.uid} has no mappable value."
                    )
                mapping = self._get_mapping_in_mapper_for_value(
                    mapper, attribute.mappable_value, session
                )
                if mapping is not None:
                    self._logger.debug(
                        f"Attribute {attribute.uid} with value {attribute.mappable_value} is now mapped."
                    )
                    self._set_display_value(mapping.attribute)
                    attribute.set_mapped_value(mapping.attribute.original_value)
                    attribute.set_mapping_item_uid(mapping.uid)
                else:
                    self._logger.debug(
                        f"Attribute {attribute.uid} with value {attribute.mappable_value} is still not mapped."
                    )

    def _apply_mappers_to_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        mappers_to_use: Iterable[Union[Mapper, DatabaseMapper, UUID]],
        validate: bool,
        session: Session,
    ) -> Iterable[AnyAttribute]:

        for attribute in attributes:
            mappers = self._database_service.get_mappers_for_root_attribute(
                session,
                attribute.schema_uid,
                [
                    mapper if isinstance(mapper, UUID) else mapper.uid
                    for mapper in mappers_to_use
                ],
            ).all()

            attribute = self._apply_mappers_to_root_attribute(
                session, mappers, attribute, validate=validate
            )
            yield attribute

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
            self._apply_mappers_to_root_attribute(
                session, [mapper], root_attribute.model, mapping.expression, validate
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

    def _apply_mappers_to_root_attribute(
        self,
        session: Session,
        mappers: Sequence[DatabaseMapper],
        attribute: AnyAttribute,
        expression: Optional[str] = None,
        validate: bool = True,
    ) -> AnyAttribute:

        if attribute.mappable_value is not None:
            root_mapper = next(
                (
                    mapper
                    for mapper in mappers
                    if mapper.root_attribute_schema_uid == mapper.attribute_schema_uid
                ),
                None,
            )
            if root_mapper is not None:
                matching_expression = self._get_matching_expression(
                    session, root_mapper, attribute, expression
                )
                if matching_expression is not None:
                    mapping = self._database_service.get_mapping_for_expression(
                        session, root_mapper.uid, matching_expression
                    )
                    attribute.mapped_value = mapping.attribute.original_value
                    attribute.mapping_item_uid = mapping.uid
                    mapping.increment_hits()
        elif isinstance(attribute, ListAttribute) and attribute.value is not None:
            mapped_value = [
                self._recursive_mapping(session, mappers, item)
                for item in attribute.value
            ]
            attribute.original_value = mapped_value

        elif isinstance(attribute, UnionAttribute) and attribute.value is not None:
            mapped_value = self._recursive_mapping(session, mappers, attribute.value)
            attribute.original_value = mapped_value
        elif isinstance(attribute, ObjectAttribute) and attribute.value is not None:
            mapped_value = {
                tag: self._recursive_mapping(session, mappers, item)
                for tag, item in attribute.value.items()
            }
            attribute.original_value = mapped_value
        if validate:
            self._validation_service.validate_attribute(attribute, session)
        self._set_display_value(attribute)
        return attribute  # type: ignore[return]

    def _recursive_mapping(
        self,
        session: Session,
        mappers: Sequence[DatabaseMapper],
        attribute: AnyAttribute,
        expression: Optional[str] = None,
    ) -> AnyAttribute:

        if attribute.mappable_value is not None:
            matching_mapper = next(
                (
                    mapper
                    for mapper in mappers
                    if mapper.attribute_schema_uid == attribute.schema_uid
                ),
                None,
            )
            if matching_mapper is not None:
                matching_expression = self._get_matching_expression(
                    session, matching_mapper, attribute, expression
                )
                if matching_expression is not None:
                    mapping = self._database_service.get_mapping_for_expression(
                        session, matching_mapper.uid, matching_expression
                    )
                    self._logger.debug(
                        f"Applying mapping {matching_expression} with value {mapping.attribute.original_value} to attribute {attribute.uid}"
                    )
                    mapping.increment_hits()
                    attribute.mapped_value = mapping.attribute.original_value
                    attribute.mapping_item_uid = mapping.uid
                    attribute.display_value = mapping.attribute.display_value
        elif (
            isinstance(attribute, ListAttribute)
            and attribute.original_value is not None
        ):
            for child_attribute in attribute.original_value:
                self._recursive_mapping(session, mappers, child_attribute)
        elif (
            isinstance(attribute, ObjectAttribute)
            and attribute.original_value is not None
        ):
            for tag, child_attribute in attribute.original_value.items():
                self._recursive_mapping(session, mappers, child_attribute)
        self._set_display_value(attribute)
        return attribute

    def _set_display_value(self, attribute: Attribute) -> None:
        """Set the display value for an attribute based on its schema."""
        if attribute.value is None:
            attribute.display_value = None
            return
        schema = self._schema_service.get_any_attribute(attribute.schema_uid)
        attribute.display_value = schema.create_display_value(attribute.value)

    def remap_item(self, item_uid: UUID, session: Optional[Session] = None) -> None:
        """Re-apply the project's mappers to one item's attributes."""
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_item(session, item_uid)
            project_mappers = self._project_mappers_for_item(item)
            if not project_mappers:
                return
            self._remap_item_attributes(session, item, project_mappers)

    def remap_item_hierarchy(
        self, item_uid: UUID, session: Optional[Session] = None
    ) -> None:
        """Re-apply mappers to the item and all of its descendants
        (child samples, images, annotations, observations)."""
        with self._database_service.get_session(session) as session:
            root = self._database_service.get_item(session, item_uid)
            project_mappers = self._project_mappers_for_item(root)
            if not project_mappers:
                return
            for descendant in self._database_service.walk_item_descendants(root):
                self._remap_item_attributes(session, descendant, project_mappers)
                session.commit()

    def remap_batch(self, batch_uid: UUID, session: Optional[Session] = None) -> None:
        """Re-apply mappers to every item in a batch.

        Refuses if the batch is in a transient state (downloading,
        pre/post-processing, storing, searching, deleted).
        """
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch_uid)
            self._require_stable_batch(batch.status, batch_uid)
            project_mappers = [
                mapper
                for group in batch.project.mapper_groups
                for mapper in group.mappers
            ]
            if not project_mappers:
                return
            for item in self._database_service.get_items_in_batch(session, batch_uid):
                self._remap_item_attributes(session, item, project_mappers)
                session.commit()

    def remap_dataset(
        self, dataset_uid: UUID, session: Optional[Session] = None
    ) -> None:
        """Re-apply mappers to every item in a dataset. Refuses unless
        every batch in the dataset's owning project is in a stable
        state."""
        with self._database_service.get_session(session) as session:
            dataset = self._database_service.get_dataset(session, dataset_uid)
            project = dataset.project
            if project is None:
                raise NotAllowedActionError(
                    f"Cannot remap dataset {dataset_uid}: no project owns it."
                )
            for batch in project.batches:
                self._require_stable_batch(batch.status, batch.uid)
            project_mappers = [
                mapper for group in project.mapper_groups for mapper in group.mappers
            ]
            if not project_mappers:
                return
            for item in self._database_service.get_items_in_dataset(
                session, dataset_uid
            ):
                self._remap_item_attributes(session, item, project_mappers)
                session.commit()

    def _require_stable_batch(self, status: BatchStatus, batch_uid: UUID) -> None:
        if status not in self._STABLE_BATCH_STATUSES:
            raise NotAllowedActionError(
                f"Cannot remap batch {batch_uid}: batch is in transient "
                f"status {status.name}."
            )

    def _project_mappers_for_item(self, item: DatabaseItem) -> list[DatabaseMapper]:
        if item.batch is None:
            return []
        return [
            mapper
            for group in item.batch.project.mapper_groups
            for mapper in group.mappers
        ]

    def _remap_item_attributes(
        self,
        session: Session,
        item: DatabaseItem,
        project_mappers: Sequence[DatabaseMapper],
    ) -> None:
        for database_attribute in item.attributes:
            self._remap_one_attribute(session, database_attribute, project_mappers)
            self._validation_service.validate_item_attributes(item, session=session)

    def _remap_one_attribute(
        self,
        session: Session,
        database_attribute: DatabaseAttribute,
        project_mappers: Sequence[DatabaseMapper],
    ) -> None:
        attribute_model = database_attribute.model
        applicable = self._database_service.get_mappers_for_root_attribute(
            session,
            attribute_model.schema_uid,
            [mapper.uid for mapper in project_mappers],
        ).all()
        if not applicable:
            return
        mapped_attribute = self._apply_mappers_to_root_attribute(
            session, applicable, attribute_model, validate=False
        )
        self._attribute_service.update(
            mapped_attribute, validate=False, session=session
        )
