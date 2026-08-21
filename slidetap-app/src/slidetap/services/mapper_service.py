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
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from re import Pattern
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseCodeAttribute,
    DatabaseMapper,
    DatabaseMapperGroup,
    DatabaseMappingItem,
    NotAllowedActionError,
)
from slidetap.database.item import DatabaseItem
from slidetap.external_interfaces import MapperInjectorInterface
from slidetap.model import (
    AnyAttribute,
    Attribute,
    AttributeSchema,
    BatchStatus,
    CodeAttribute,
    CodeSuggestion,
    ListAttribute,
    Mapper,
    MapperGroup,
    MappingItem,
    ObjectAttribute,
    RejectedValues,
    UnionAttribute,
)
from slidetap.model.mapper import MapperCreate, MappingItemCreate
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.review_service import ReviewService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


@dataclass
class MapperCache:
    """Mapper reads held for the length of one import.

    Which mappers apply to an attribute schema, and which mapping items a
    mapper holds, are the same answer for every attribute of every result in
    an import, so asking per attribute is a query per attribute -- and a query
    while a result is being stored writes the result out, which is what stops
    its rows going out in batches.

    Primed, it answers from whole mapping items held in memory, so the ordering
    a resolve depends on is read off their live ``hits`` and stays what it
    would have been. Unprimed, every lookup falls through to the query it
    replaces, so nothing depends on a caller having primed it.

    What it holds are rows of the session it was primed from, so it lasts as
    long as that session and no longer. Kept across sessions -- one per batch
    rather than one per result, say -- every read of it past the first raises
    ``DetachedInstanceError``.
    """

    mappers_for_root: dict[UUID, list[DatabaseMapper]] = field(default_factory=dict)
    """The mappers of an attribute schema, by that schema's uid."""

    items_by_mapper: dict[UUID, list[DatabaseMappingItem]] = field(
        default_factory=dict
    )
    """A mapper's mapping items, hits-ordered as first read. Membership is also
    what says a mapper has been primed."""


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
        review_service: ReviewService,
        mapper_injector: MapperInjectorInterface | None = None,
    ):
        self._attribute_service = attribute_service
        self._validation_service = validation_service
        self._schema_service = schema_service
        self._database_service = database_service
        self._review_service = review_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if mapper_injector is not None:
            self._inject(mapper_injector)

    def _inject(self, mapper_injector: MapperInjectorInterface) -> None:
        injected_expressions: set[tuple[UUID, str]] = set()
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
                        if (mapper.uid, item.expression) in injected_expressions:
                            self._logger.warning(
                                f"Duplicate mapping expression {item.expression!r} "
                                f"for mapper {mapper.name}; keeping the first and "
                                f"skipping the duplicate."
                            )
                            continue
                        injected_expressions.add((mapper.uid, item.expression))
                        self.get_or_create_mapping(
                            mapper.uid,
                            item.expression,
                            item.attribute,
                            session=session,
                        )
                session.flush()
                self.add_mappers_to_group(group, group_mappers, session=session)

    @staticmethod
    @lru_cache(1000)
    def create_pattern(pattern: str) -> Pattern:
        return re.compile(pattern)

    def get_all_mapper_groups(
        self, session: Session | None = None
    ) -> Sequence[MapperGroup]:
        with self._database_service.get_session(session) as session:
            groups = self._database_service.get_mapper_groups(
                session, load_relations=True
            )
            return [group.model for group in groups]

    def get_or_create_mapper_group(
        self,
        name: str,
        default_enabled: bool,
        session: Session | None = None,
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
        session: Session | None = None,
    ) -> MapperGroup:
        with self._database_service.get_session(session) as session:
            database_group = self._database_service.get_mapper_group(session, group.uid)
            for mapper in mappers:
                self._logger.debug(f"Adding mapper {mapper.uid} to group {group.uid}")
                database_mapper = self._database_service.get_mapper(session, mapper.uid)
                if database_mapper not in database_group.mappers:
                    database_group.mappers.add(database_mapper)
            return database_group.model

    def set_mappers_in_group(
        self,
        group_uid: UUID,
        mapper_uids: Iterable[UUID],
        session: Session | None = None,
    ) -> MapperGroup | None:
        """Replace the mappers of a group with the given mappers.

        Returns None if there is no group with the given uid, or if any of the
        given mappers does not exist.
        """
        with self._database_service.get_session(session) as session:
            database_group = self._database_service.get_optional_mapper_group(
                session, group_uid
            )
            if database_group is None:
                return None
            mappers = set()
            for mapper_uid in mapper_uids:
                mapper = self._database_service.get_optional_mapper(session, mapper_uid)
                if mapper is None:
                    return None
                mappers.add(mapper)
            database_group.mappers = mappers
            session.flush()
            return database_group.model

    def get_or_create_mapper(
        self,
        name: str,
        attribute_schema: UUID | AttributeSchema,
        root_attribute_schema: UUID | AttributeSchema | None = None,
        session: Session | None = None,
    ) -> Mapper:
        if isinstance(attribute_schema, AttributeSchema):
            attribute_schema = attribute_schema.uid
        if isinstance(root_attribute_schema, AttributeSchema):
            root_attribute_schema = root_attribute_schema.uid
        if root_attribute_schema is None:
            root_attribute_schema = attribute_schema
        with self._database_service.get_session(session) as session:
            existing_mapper = self._database_service.get_mapper_by_name(session, name)
            if existing_mapper is not None:
                return existing_mapper.model
            # The table is unique on the schema pair, not the name, so a mapper
            # that has been renamed since it was injected is still there under
            # the old name. Rename it rather than inserting a second one for the
            # same pair, which the constraint rejects.
            existing_mapper = self._database_service.get_mapper_for_schemas(
                session, attribute_schema, root_attribute_schema
            )
            if existing_mapper is not None:
                existing_mapper.name = name
                return existing_mapper.model
            mapper = self._create_mapper(
                session, name, attribute_schema, root_attribute_schema
            )
            return mapper.model

    def get_or_create_mapping(
        self,
        mapper_uid: UUID,
        expression: str,
        attribute: AnyAttribute,
        apply: bool = False,
        session: Session | None = None,
    ) -> MappingItem:
        with self._database_service.get_session(session) as session:
            existing_mapping = (
                self._database_service.get_optional_mapping_for_expression(
                    session, mapper_uid, expression
                )
            )
            if existing_mapping is not None:
                return existing_mapping.model
            self._attribute_service.set_display_value(attribute)
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

    def get_mapper(self, mapper_uid: UUID) -> Mapper | None:
        with self._database_service.get_session() as session:
            mapper = self._database_service.get_optional_mapper(session, mapper_uid)
            return mapper.model if mapper is not None else None

    def get_mapping(self, mapping_uid: UUID) -> MappingItem | None:
        with self._database_service.get_session() as session:
            mapping = self._database_service.get_optional_mapping(session, mapping_uid)
            return mapping.model if mapping is not None else None

    def get_mappings_for_mapper(self, mapper_uid: UUID) -> Sequence[MappingItem]:
        with self._database_service.get_session() as session:
            mappings = self._database_service.get_mappings_for_mapper(
                session, mapper_uid
            )
            return [mapping.model for mapping in mappings]

    def get_mapping_for_attribute(self, attribute: Attribute) -> MappingItem | None:
        pass

    def search_codes_for_attribute_schema(
        self,
        attribute_schema_uid: UUID,
        query: str,
        limit: int = 20,
    ) -> list[CodeSuggestion]:
        """Suggest Codes for a CodeAttribute schema.

        Combines two sources:

        1. Mapping items belonging to mappers bound to the schema. Each match
           carries the source ``mappable_value`` (e.g. an M-code) and
           ``mapping_item_uid`` so the UI can render the M-code → Code
           relationship.
        2. Previously stored ``CodeAttribute`` values for the same schema, so
           Codes that were entered or edited directly (without ever being the
           target of a mapping) still surface as suggestions.

        The query (case-insensitive substring) is matched against the mapping
        expression, the Code's ``code``, or the Code's ``meaning``. An empty
        query returns the most frequently used mappings first, then arbitrary
        stored Codes up to the limit.
        """
        normalized_query = query.strip().casefold()
        with self._database_service.get_session() as session:
            suggestions: list[CodeSuggestion] = []
            seen_direct: set[tuple[str, str]] = set()

            mappers = session.scalars(
                select(DatabaseMapper).filter_by(
                    attribute_schema_uid=attribute_schema_uid
                )
            ).all()
            if mappers:
                mapper_uids = [mapper.uid for mapper in mappers]
                mapping_items = list(
                    self._database_service.get_mappings_for_mappers(
                        session, mapper_uids
                    )
                )
                for item in mapping_items:
                    attribute_model = item.attribute
                    if not isinstance(attribute_model, CodeAttribute):
                        continue
                    code = attribute_model.value or attribute_model.original_value
                    if code is None:
                        continue

                    match: Literal["code", "meaning", "mappable"] | None = None
                    if (
                        normalized_query == ""
                        or normalized_query in item.expression.casefold()
                    ):
                        match = "mappable"
                    elif normalized_query in code.code.casefold():
                        match = "code"
                    elif code.meaning and normalized_query in code.meaning.casefold():
                        match = "meaning"
                    if match is None:
                        continue

                    if match == "mappable":
                        suggestions.append(
                            CodeSuggestion(
                                code=code,
                                match=match,
                                mappable_value=item.expression,
                                mapping_item_uid=item.uid,
                            )
                        )
                    else:
                        key = (code.code, code.scheme)
                        if key in seen_direct:
                            continue
                        seen_direct.add(key)
                        suggestions.append(CodeSuggestion(code=code, match=match))

                    if len(suggestions) >= limit:
                        return suggestions

            stored_query = select(DatabaseCodeAttribute).filter_by(
                schema_uid=attribute_schema_uid
            )
            if normalized_query:
                pattern = f"%{normalized_query}%"
                stored_query = stored_query.where(
                    func.lower(DatabaseCodeAttribute.display_value).like(pattern)
                )
            # Cap the SQL scan so this stays fast on large tables; the Python
            # loop below stops once we hit `limit` matches.
            stored_query = stored_query.limit(max(limit * 10, 200))

            for db_attr in session.scalars(stored_query):
                code = db_attr.value or db_attr.original_value
                if code is None or code.code == "":
                    continue
                key = (code.code, code.scheme)
                if key in seen_direct:
                    continue

                if normalized_query == "" or normalized_query in code.code.casefold():
                    match_kind: Literal["code", "meaning"] = "code"
                elif code.meaning and normalized_query in code.meaning.casefold():
                    match_kind = "meaning"
                else:
                    continue

                seen_direct.add(key)
                suggestions.append(CodeSuggestion(code=code, match=match_kind))
                if len(suggestions) >= limit:
                    break

            return suggestions

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
                session, mapping.mapper_uid, mapping.expression, mapping.attribute
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

    def delete_mapper(self, mapper_uid: UUID) -> bool:
        """Delete a mapper and the mappings belonging to it.

        Returns False if there is no mapper with the given uid.
        """
        with self._database_service.get_session() as session:
            mapper = self._database_service.get_optional_mapper(session, mapper_uid)
            if mapper is None:
                return False
            mappings = self._database_service.get_mappings_for_mapper(
                session, mapper_uid
            )
            self._clear_mapping_from_attributes(
                session, [mapping.uid for mapping in mappings]
            )
            for mapping in mappings:
                session.delete(mapping)
            session.flush()
            session.delete(mapper)
            return True

    def delete_mapping(self, mapping_uid: UUID) -> bool:
        """Delete a mapping.

        Returns False if there is no mapping with the given uid.
        """
        with self._database_service.get_session() as session:
            mapping = self._database_service.get_optional_mapping(session, mapping_uid)
            if mapping is None:
                return False
            self._clear_mapping_from_attributes(session, [mapping.uid])
            session.flush()
            session.delete(mapping)
            return True

    @staticmethod
    def _clear_mapping_from_attributes(
        session: Session, mapping_uids: Sequence[UUID]
    ) -> None:
        """Clear the mapped value of the attributes mapped by the given mappings.

        Attributes reference the mapping they were mapped by, so the reference
        has to go before the mapping can be deleted. Only root attributes are
        rows, a nested attribute keeps the reference in the value of its root
        attribute until the item is remapped, which is harmless as it is not a
        foreign key.

        ponytail: assigns the columns rather than calling `clear_mapping`, so
        that a locked or read only attribute does not block deleting a mapper.
        """
        if len(mapping_uids) == 0:
            return
        attributes = session.scalars(
            select(DatabaseAttribute).where(
                DatabaseAttribute.mapping_item_uid.in_(mapping_uids)
            )
        )
        for attribute in attributes:
            attribute.mapping_item_uid = None
            # The mapped value is typed by the attribute type, which the attribute
            # cannot be narrowed to while it is one of a union of attribute types.
            cast(Any, attribute).mapped_value = None

    def apply_mappers_to_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        project_mappers: Iterable[Mapper | DatabaseMapper | UUID],
        validate: bool = True,
        session: Session | None = None,
        cache: MapperCache | None = None,
    ) -> Iterable[AnyAttribute]:
        with self._database_service.get_session(session) as session:
            yield from self._apply_mappers_to_attributes(
                attributes, project_mappers, validate, session, cache
            )

    def apply_mapper_to_unmapped_attributes(
        self, mapper: Mapper, session: Session | None = None
    ):
        with self._database_service.get_session(session) as session:
            mappable_attributes = self._get_mappable_attributes_for_mapper(
                mapper, session
            )
            for attribute in mappable_attributes:
                self._logger.debug(
                    f"Trying to map attribute {attribute.uid} "
                    f"with value {attribute.mappable_value}"
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
                        f"Attribute {attribute.uid} with value "
                        f"{attribute.mappable_value} is now mapped."
                    )
                    self._attribute_service.set_display_value(mapping.attribute)
                    attribute.set_mapped_value(mapping.attribute.original_value)
                    attribute.set_mapping_item_uid(mapping.uid)
                else:
                    self._logger.debug(
                        f"Attribute {attribute.uid} with value "
                        f"{attribute.mappable_value} is still not mapped."
                    )

    def prime_cache(
        self,
        session: Session,
        cache: MapperCache,
        attribute_schema_uids: Iterable[UUID],
        mappers_to_use: Iterable[Mapper | DatabaseMapper | UUID],
    ) -> None:
        """Read what mapping the given attribute schemas needs, in two queries.

        Called before storing a group so that mapping it asks the database for
        nothing: what is not primed is fetched where it is needed, and where it
        is needed is between one item and the next.
        """
        mapper_uids = [
            mapper if isinstance(mapper, UUID) else mapper.uid
            for mapper in mappers_to_use
        ]
        wanted = [uid for uid in set(attribute_schema_uids) if uid not in cache.mappers_for_root]
        if not wanted or not mapper_uids:
            for uid in wanted:
                cache.mappers_for_root[uid] = []
            return
        for uid in wanted:
            cache.mappers_for_root[uid] = []
        for mapper in self._database_service.get_mappers_for_root_attributes(
            session, wanted, mapper_uids
        ):
            cache.mappers_for_root[mapper.root_attribute_schema_uid].append(mapper)
        unprimed = {
            mapper.uid
            for uid in wanted
            for mapper in cache.mappers_for_root[uid]
            if mapper.uid not in cache.items_by_mapper
        }
        for mapper_uid in unprimed:
            cache.items_by_mapper[mapper_uid] = []
        for item in self._database_service.get_mapping_items_for_mappers(
            session, unprimed
        ):
            cache.items_by_mapper[item.mapper_uid].append(item)

    def _cached_mappers_for_root(
        self,
        session: Session,
        root_attribute_schema_uid: UUID,
        mapper_uids: Sequence[UUID],
        cache: MapperCache | None,
    ) -> list[DatabaseMapper]:
        """The mappers that apply, from the cache when it holds them."""
        if cache is None:
            return self._database_service.get_mappers_for_root_attribute(
                session, root_attribute_schema_uid, mapper_uids
            ).all()
        if root_attribute_schema_uid not in cache.mappers_for_root:
            cache.mappers_for_root[root_attribute_schema_uid] = (
                self._database_service.get_mappers_for_root_attribute(
                    session, root_attribute_schema_uid, mapper_uids
                ).all()
            )
        return cache.mappers_for_root[root_attribute_schema_uid]

    def _cached_regex_items(
        self, session: Session, mapper_uid: UUID, cache: MapperCache | None
    ) -> Iterable[Row[tuple[str, int, UUID]] | DatabaseMappingItem]:
        """The mapper's regex-shaped mapping items, hits-ordered.

        Ordered here rather than by the database when the cache holds them,
        since their hits move as they are applied.
        """
        if cache is None or mapper_uid not in cache.items_by_mapper:
            return self._database_service.get_regex_mapping_items(session, mapper_uid)
        return sorted(
            (
                item
                for item in cache.items_by_mapper[mapper_uid]
                if item.literal is None
            ),
            key=lambda item: (-item.hits, item.uid),
        )

    def _cached_literal_item(
        self,
        session: Session,
        mapper_uid: UUID,
        value: str,
        cache: MapperCache | None,
    ) -> Row[tuple[str, int, UUID]] | DatabaseMappingItem | None:
        """The mapping item whose literal is exactly this value, the most hit
        of them where there is more than one."""
        if cache is None or mapper_uid not in cache.items_by_mapper:
            return self._database_service.get_literal_mapping_candidate(
                session, mapper_uid, value
            )
        candidates = [
            item
            for item in cache.items_by_mapper[mapper_uid]
            if item.literal == value
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: (-item.hits, item.uid))

    def _cached_mapping_for_expression(
        self,
        session: Session,
        mapper_uid: UUID,
        expression: str,
        cache: MapperCache | None,
    ) -> DatabaseMappingItem:
        """The mapping item for an expression."""
        if cache is not None and mapper_uid in cache.items_by_mapper:
            for item in cache.items_by_mapper[mapper_uid]:
                if item.expression == expression:
                    return item
        return self._database_service.get_mapping_for_expression(
            session, mapper_uid, expression
        )

    def _apply_mappers_to_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        mappers_to_use: Iterable[Mapper | DatabaseMapper | UUID],
        validate: bool,
        session: Session,
        cache: MapperCache | None = None,
    ) -> Iterable[AnyAttribute]:
        mapper_uids = [
            mapper if isinstance(mapper, UUID) else mapper.uid
            for mapper in mappers_to_use
        ]
        for attribute in attributes:
            mappers = self._cached_mappers_for_root(
                session, attribute.schema_uid, mapper_uids, cache
            )

            attribute = self._apply_mappers_to_root_attribute(
                session, mappers, attribute, validate=validate, cache=cache
            )
            yield attribute

    def _get_mapping_in_mapper_for_value(
        self, mapper: Mapper, value: str, session: Session
    ) -> DatabaseMappingItem | None:
        expression = self._resolve_expression(session, mapper.uid, value)
        if expression is None:
            return None
        return self._get_mapping_for_expression_in_mapper(mapper, expression, session)

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
        attribute_schema: UUID | AttributeSchema,
        root_attribute_schema: UUID | AttributeSchema | None = None,
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

    @staticmethod
    def _copy_mapped_value(target: AnyAttribute, source: AnyAttribute) -> None:
        """Copy ``source.original_value`` to ``target.mapped_value``.

        Target and source are required to be of the same attribute type, as the
        values of an attribute are of the type of the attribute. A mismatch is
        raised on, rather than silently written as a value of the wrong type.
        """
        if type(target) is not type(source):
            raise TypeError(
                f"Cannot copy mapped value across mismatched attribute types: "
                f"target={type(target).__name__}, source={type(source).__name__}"
            )
        # The attributes are of the same type, and the value of the source is thus of
        # the type of the value of the target, which the target cannot be narrowed to
        # while it is one of a union of attribute types.
        cast(Attribute[Any], target).mapped_value = source.original_value

    def _get_matching_expression(
        self,
        session: Session,
        mapper: DatabaseMapper,
        attribute: Attribute | DatabaseAttribute,
        expression: str | None = None,
        cache: MapperCache | None = None,
    ):
        value = attribute.mappable_value
        if value is None:
            return None
        if expression is not None:
            # Caller is checking one specific expression (applying a single new
            # or edited mapping to every attribute); no index needed.
            pattern = self.create_pattern(expression)
            if pattern.match(value) is None:
                return None
            return expression
        return self._resolve_expression(session, mapper.uid, value, cache)

    def _resolve_expression(
        self,
        session: Session,
        mapper_uid: UUID,
        value: str,
        cache: MapperCache | None = None,
    ) -> str | None:
        """Resolve ``value`` to the winning mapping key for a mapper.

        An exact-literal lookup (index seek on `(mapper_uid, literal)`) plus a
        scan of only the mapper's genuinely regex-shaped expressions, in place
        of a scan over every expression. The winner is whichever candidate
        sorts first under `(hits desc, uid)`, which is exactly the ordering
        `_linear_scan_expression` scans in, so the result is identical to a
        full linear scan.
        """
        if "\n" in value:
            # `$` in an exact `^literal$` key also matches before a trailing
            # newline under re.match ("^X$" matches "X\n"), which an exact
            # string-equality lookup on `literal` would miss. Route any
            # newline-bearing value through the authoritative scan to stay
            # byte-identical to a full linear scan. Pathological for coded
            # values; never on the hot path.
            return self._linear_scan_expression(session, mapper_uid, value)

        candidates: list[Row[tuple[str, int, UUID]]] = []
        exact = self._cached_literal_item(session, mapper_uid, value, cache)
        if exact is not None:
            candidates.append(exact)
        candidates.extend(
            item
            for item in self._cached_regex_items(session, mapper_uid, cache)
            if self.create_pattern(item.expression).match(value) is not None
        )
        if not candidates:
            return None
        winner = min(candidates, key=lambda item: (-item.hits, item.uid))
        return winner.expression

    def _linear_scan_expression(
        self, session: Session, mapper_uid: UUID, value: str
    ) -> str | None:
        """Authoritative fallback: first expression matching ``value`` in the
        mapper's live hits-ordered expression list."""
        return next(
            (
                expression
                for expression in self._database_service.get_mapper_expressions(
                    session, mapper_uid
                )
                if self.create_pattern(expression).match(value)
            ),
            None,
        )

    def _apply_mappers_to_root_attribute(
        self,
        session: Session,
        mappers: Sequence[DatabaseMapper],
        attribute: AnyAttribute,
        expression: str | None = None,
        validate: bool = True,
        cache: MapperCache | None = None,
    ) -> AnyAttribute:

        # A refused mappable is out of mapping altogether: re-running the
        # mappers neither replaces what it produced nor revives it.
        if (
            attribute.mappable_value is not None
            and RejectedValues.MAPPABLE not in attribute.rejected
        ):
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
                    session, root_mapper, attribute, expression, cache
                )
                if matching_expression is not None:
                    mapping = self._cached_mapping_for_expression(
                        session, root_mapper.uid, matching_expression, cache
                    )
                    self._copy_mapped_value(attribute, mapping.attribute)
                    attribute.mapping_item_uid = mapping.uid
                    mapping.increment_hits()
        elif isinstance(attribute, ListAttribute) and attribute.value is not None:
            mapped_value = [
                self._recursive_mapping(session, mappers, item, cache=cache)
                for item in attribute.value
            ]
            attribute.original_value = mapped_value

        elif isinstance(attribute, UnionAttribute) and attribute.value is not None:
            mapped_value = self._recursive_mapping(
                session, mappers, attribute.value, cache=cache
            )
            attribute.original_value = mapped_value
        elif isinstance(attribute, ObjectAttribute) and attribute.value is not None:
            mapped_value = {
                tag: self._recursive_mapping(session, mappers, item, cache=cache)
                for tag, item in attribute.value.items()
            }
            attribute.original_value = mapped_value
        if validate:
            self._validation_service.validate_attribute(attribute, session)
        self._attribute_service.set_display_value(attribute)
        return attribute

    def _recursive_mapping(
        self,
        session: Session,
        mappers: Sequence[DatabaseMapper],
        attribute: AnyAttribute,
        expression: str | None = None,
        cache: MapperCache | None = None,
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
                    session, matching_mapper, attribute, expression, cache
                )
                if matching_expression is not None:
                    mapping = self._cached_mapping_for_expression(
                        session, matching_mapper.uid, matching_expression, cache
                    )
                    self._logger.debug(
                        f"Applying mapping {matching_expression} with value "
                        f"{mapping.attribute.original_value} "
                        f"to attribute {attribute.uid}"
                    )
                    mapping.increment_hits()
                    self._copy_mapped_value(attribute, mapping.attribute)
                    attribute.mapping_item_uid = mapping.uid
                    attribute.display_value = mapping.attribute.display_value
        elif (
            isinstance(attribute, ListAttribute)
            and attribute.original_value is not None
        ):
            for child_attribute in attribute.original_value:
                self._recursive_mapping(
                    session, mappers, child_attribute, cache=cache
                )
        elif (
            isinstance(attribute, ObjectAttribute)
            and attribute.original_value is not None
        ):
            for child_attribute in attribute.original_value.values():
                self._recursive_mapping(
                    session, mappers, child_attribute, cache=cache
                )
        self._attribute_service.set_display_value(attribute)
        return attribute

    def remap_item(self, item_uid: UUID, session: Session | None = None) -> None:
        """Re-apply the project's mappers to one item's attributes."""
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_item(session, item_uid)
            project_mappers = self._project_mappers_for_item(item)
            if not project_mappers:
                return
            self._remap_item_attributes(session, item, project_mappers)

    def remap_item_hierarchy(
        self, item_uid: UUID, session: Session | None = None
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

    def remap_batch(self, batch_uid: UUID, session: Session | None = None) -> None:
        """Re-apply mappers to every item in a batch.

        Refuses if the batch is in a transient state (downloading,
        pre/post-processing, storing, searching, deleted).
        """
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch_uid)
            self._require_stable_batch(batch.status, batch_uid)
            project_mappers = self._mappers_in_groups(batch.project.mapper_groups)
            if not project_mappers:
                return
            for item in self._database_service.get_items_in_batch(
                session, batch_uid, load_attributes=True
            ):
                self._remap_item_attributes(session, item, project_mappers)
                session.commit()

    def remap_dataset(self, dataset_uid: UUID, session: Session | None = None) -> None:
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
            project_mappers = self._mappers_in_groups(project.mapper_groups)
            if not project_mappers:
                return
            for item in self._database_service.get_items_in_dataset(
                session, dataset_uid, load_attributes=True
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
        return self._mappers_in_groups(item.batch.project.mapper_groups)

    @staticmethod
    def _mappers_in_groups(
        groups: Iterable[DatabaseMapperGroup],
    ) -> list[DatabaseMapper]:
        """Return the mappers of the groups, each mapper once.

        A mapper can belong to several groups, and a project can use several
        groups, so the same mapper can be reached more than once.
        """
        mappers: dict[UUID, DatabaseMapper] = {}
        for group in groups:
            for mapper in group.mappers:
                mappers.setdefault(mapper.uid, mapper)
        return list(mappers.values())

    def _remap_item_attributes(
        self,
        session: Session,
        item: DatabaseItem,
        project_mappers: Sequence[DatabaseMapper],
    ) -> None:
        # Read before the remap, and once for the item rather than once per
        # attribute: what is worth recording is the item crossing between valid
        # and not, not that it was validated once for every attribute it has.
        was_valid = self._validation_service.item_is_valid_for_now(item, session)
        for database_attribute in item.attributes:
            self._remap_one_attribute(session, database_attribute, project_mappers)
            self._validation_service.validate_item_attributes(item, session=session)
        self._review_service.item_validity_changed(
            item.uid,
            was_valid,
            self._validation_service.item_is_valid_for_now(item, session),
            session=session,
        )

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
