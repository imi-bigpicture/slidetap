#    Copyright 2026 SECTRA AB
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

"""Writing the planned migration of a project to the database."""

import dataclasses
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import ClassVar
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from slidetap.database import (
    DatabaseAttribute,
    DatabaseAttributeMigrationIssue,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    Item,
    Project,
    RootSchemaIndex,
    UnresolvedAttributeMigration,
)
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.migration.project_migration_planner import (
    EntityInMigration,
    ProjectMigrationPlan,
)
from slidetap.services.review_service import ReviewService
from slidetap.services.validation_service import ValidationService


class ProjectMigrationExecutor:
    """Writes the migration of a project in a session: puts the resolved values
    at their tags, replaces the attributes of every entity, moves the search
    items and the project to the target root, and validates the project again.
    """

    CHUNK_SIZE: ClassVar[int] = 2000
    """How many entities are written at a time, with one flush."""

    def __init__(
        self,
        database_service: DatabaseService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
    ):
        """Create the executor.

        Parameters
        ----------
        database_service: DatabaseService
            For the rows of the project.
        attribute_service: AttributeService
            For the display values of attributes.
        validation_service: ValidationService
            For validating the project on the target root.
        review_service: ReviewService
            For flagging review units left invalid.
        """
        self._database_service = database_service
        self._attribute_service = attribute_service
        self._validation_service = validation_service
        self._review_service = review_service

    def execute(
        self,
        session: Session,
        database_project: DatabaseProject,
        plan: ProjectMigrationPlan,
        resolutions: Mapping[tuple[UUID, UUID], DatabaseAttributeMigrationIssue],
        progress: Callable[[int], None] | None = None,
    ) -> None:
        """Put the resolved values at their tags, replace the attributes of
        every entity, and move the search items and the project to the target
        root.

        Parameters
        ----------
        session: Session
            The session to write the migration in.
        database_project: DatabaseProject
            The project.
        plan: ProjectMigrationPlan
            The migration of the project, planned again.
        resolutions: Mapping[tuple[UUID, UUID], DatabaseAttributeMigrationIssue]
            The resolved attribute issues with a target, by entity uid and
            target attribute schema uid, with one for each unresolved
            attribute.
        progress: Callable[[int], None] | None = None
            Told of the entities written, with how many, a chunk at a time.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        for start in range(0, len(plan.entities), self.CHUNK_SIZE):
            chunk = [
                self._apply_resolutions(entity, resolutions)
                for entity in plan.entities[start : start + self.CHUNK_SIZE]
            ]
            self._write_chunk(session, chunk)
            if progress is not None:
                progress(len(chunk))
        for search_item in plan.search_items:
            database_search_item = self._database_service.get_metadata_search_item(
                session, search_item.source.uid
            )
            database_search_item.schema_uid = search_item.target_schema.uid
        database_project.root_schema_uid = plan.target_root.uid

    def revalidate(
        self,
        session: Session,
        database_project: DatabaseProject,
        item_uids: Collection[UUID],
        progress: Callable[[int], None] | None = None,
    ) -> None:
        """Validate the project again, on the root it is on, and flag the
        review units left invalid.

        Only what the migration can have changed the validity of is validated:
        the project, the dataset, and the items it changed, with the other side
        of each of their relations. An item it left as it is keeps its schema
        and its attributes, and so its validity, but for relations to an item
        it changed.

        Parameters
        ----------
        session: Session
            The session to validate the project in.
        database_project: DatabaseProject
            The project.
        item_uids: Collection[UUID]
            The uids of the items the migration changed.
        progress: Callable[[int], None] | None = None
            Told of each item validated, with how many: one.
        """
        database_dataset = self._database_service.get_dataset(
            session, database_project.dataset_uid
        )
        self._validation_service.validate_project_attributes(database_project, session)
        self._validation_service.validate_dataset_attributes(database_dataset, session)
        # Shared, so that an item related to several changed ones has its
        # relations validated once.
        visited: set[UUID] = set()
        uids = list(item_uids)
        for start in range(0, len(uids), self.CHUNK_SIZE):
            chunk = uids[start : start + self.CHUNK_SIZE]
            # Loaded up front with their relations, and the items they relate
            # to with theirs, for validating the relations on both sides, so
            # that nothing is read, nor flushed, an item at a time.
            items = self._database_service.get_items_with_models_loaded(session, chunk)
            related = self._database_service.get_items_with_models_loaded(
                session,
                {
                    other.uid
                    for item in items.values()
                    for other in self._database_service.get_related(item)
                }
                - items.keys(),
            )
            for item_uid in chunk:
                self._validation_service.validate_item(
                    items.get(item_uid, item_uid), session, visited
                )
            if progress is not None:
                progress(len(chunk))
            del related
        self._review_service.flag_invalid_review_units(
            database_dataset.uid, session=session
        )

    @staticmethod
    def _apply_resolutions(
        entity: EntityInMigration,
        resolutions: Mapping[tuple[UUID, UUID], DatabaseAttributeMigrationIssue],
    ) -> EntityInMigration:
        """Put the resolved values at their tags, and nothing at a tag left
        empty.

        A resolved value is given the uid of the attribute it resolves, as the
        migration gives a converted one, keeping the row of the attribute and
        its lock and read only flags.

        Parameters
        ----------
        entity: EntityInMigration
            The entity, checked.
        resolutions: Mapping[tuple[UUID, UUID], DatabaseAttributeMigrationIssue]
            The resolved attribute issues with a target, by entity uid and
            target attribute schema uid, with one for each unresolved attribute
            of the entity.

        Returns
        -------
        EntityInMigration
            The entity, with the resolved values and nothing unresolved.
        """
        resolved_mappings: list[
            dict[str, AnyAttribute | UnresolvedAttributeMigration]
        ] = []
        for attributes, schemas in (
            (entity.target_attributes, entity.target_schema.attributes),
            (
                entity.target_private_attributes,
                entity.target_schema.private_attributes,
            ),
        ):
            resolved_attributes: dict[
                str, AnyAttribute | UnresolvedAttributeMigration
            ] = {}
            for tag, attribute in attributes.items():
                if not isinstance(attribute, UnresolvedAttributeMigration):
                    resolved_attributes[tag] = attribute
                    continue
                # The planner refuses an unresolved attribute off the target
                # schema, so its tag has an attribute schema.
                resolved = resolutions[(entity.source.uid, schemas[tag].uid)].resolved
                if resolved is None:
                    continue
                replaced = attribute.original or attribute.proposed
                if replaced is not None:
                    resolved = resolved.model_copy(update={"uid": replaced.uid})
                resolved_attributes[tag] = resolved
            resolved_mappings.append(resolved_attributes)
        attributes, private_attributes = resolved_mappings
        return dataclasses.replace(
            entity,
            target_attributes=attributes,
            target_private_attributes=private_attributes,
        )

    def _write_chunk(
        self, session: Session, entities: Sequence[EntityInMigration]
    ) -> None:
        """Put entities on their target schemas, and replace their attributes
        with the target ones, with one flush for them all.

        The old attributes are deleted and the target attributes inserted,
        keeping their uids, and with them the locks and read only flags of the
        old attributes of the same uid. The only rows referring to attributes
        are unmapped values, which go with them and are recorded again for the
        new attributes.

        The old attributes of every entity are deleted, and flushed, before any
        target attribute is added, as a target attribute can have the uid of an
        old one.

        Parameters
        ----------
        session: Session
            The session to write the entities in.
        entities: Sequence[EntityInMigration]
            The entities, with the resolved values and nothing unresolved.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        database_entities = self._get_database_entities(session, entities)
        # Held until the chunk is flushed, for change tracking to walk up
        # through without loading anything.
        ancestors = self._database_service.load_ancestors(
            session,
            [
                entity
                for entity in database_entities
                if isinstance(entity, DatabaseItem)
            ],
        )
        old_attributes = [
            old
            for database_entity in database_entities
            for old in (
                *database_entity.attributes,
                *database_entity.private_attributes,
            )
        ]
        flags = {old.uid: (old.read_only, old.locked) for old in old_attributes}
        if flags:
            # Deleted with them by the database, but said here for a database
            # that does not enforce its foreign keys.
            self._database_service.delete_unmapped_values(session, list(flags))
        for old in old_attributes:
            # Deleted above, so that deleting the attribute does not load them
            # to delete them with it.
            set_committed_value(old, "unmapped_values", [])
        for database_entity in database_entities:
            database_entity.attributes = set()
            database_entity.private_attributes = set()
        session.flush()
        # Mapping items a mapper move removed are referred to by nothing.
        existing_mappings = self._database_service.get_existing_mapping_uids(
            session,
            {
                uid
                for entity in entities
                for attribute in (
                    *entity.migrated_attributes.values(),
                    *entity.migrated_private_attributes.values(),
                )
                for uid in attribute.mapping_item_uids()
            },
        )
        for entity, database_entity in zip(entities, database_entities, strict=True):
            target_schema = entity.target_schema
            database_entity.schema_uid = target_schema.uid
            database_entity.attributes = self._add_attributes(
                session,
                database_entity,
                entity.migrated_attributes,
                target_schema.attributes,
                flags,
                existing_mappings,
            )
            database_entity.private_attributes = self._add_attributes(
                session,
                database_entity,
                entity.migrated_private_attributes,
                target_schema.private_attributes,
                flags,
                existing_mappings,
            )
        session.flush()
        del ancestors

    def _get_database_entities(
        self, session: Session, entities: Sequence[EntityInMigration]
    ) -> list[DatabaseProject | DatabaseDataset | DatabaseItem]:
        """Get the database entities of projects, datasets, and items, the
        items in one go with their attributes and relations.

        Parameters
        ----------
        session: Session
            The session to get them in.
        entities: Sequence[EntityInMigration]
            The entities.

        Returns
        -------
        list[DatabaseProject | DatabaseDataset | DatabaseItem]
            The database entities, in the order of the entities.
        """
        items = self._database_service.get_items_with_models_loaded(
            session,
            [
                entity.source.uid
                for entity in entities
                if isinstance(entity.source, Item)
            ],
        )
        database_entities: list[DatabaseProject | DatabaseDataset | DatabaseItem] = []
        for entity in entities:
            source = entity.source
            if isinstance(source, Project):
                database_entities.append(
                    self._database_service.get_project(session, source)
                )
            elif isinstance(source, Dataset):
                database_entities.append(
                    self._database_service.get_dataset(session, source)
                )
            elif source.uid in items:
                database_entities.append(items[source.uid])
            else:
                # Not found: raised as getting it alone would.
                database_entities.append(
                    self._database_service.get_item(session, source)
                )
        return database_entities

    def _add_attributes(
        self,
        session: Session,
        database_entity: DatabaseProject | DatabaseDataset | DatabaseItem,
        attributes: Mapping[str, AnyAttribute],
        schemas: Mapping[str, AttributeSchema],
        flags: Mapping[UUID, tuple[bool, bool]],
        existing_mappings: Collection[UUID],
    ) -> set[DatabaseAttribute]:
        """Add the target attributes of an entity.

        Parameters
        ----------
        session: Session
            The session to add them in.
        database_entity: DatabaseProject | DatabaseDataset | DatabaseItem
            The entity.
        attributes: Mapping[str, AnyAttribute]
            The target attributes, by tag.
        schemas: Mapping[str, AttributeSchema]
            The attribute schemas of the target schema, by tag.
        flags: Mapping[UUID, tuple[bool, bool]]
            The read only and locked flags of the old attributes, by uid.
        existing_mappings: Collection[UUID]
            The uids of the mapping items the attributes refer to that exist.

        Returns
        -------
        set[DatabaseAttribute]
            The added attributes.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        database_attributes: set[DatabaseAttribute] = set()
        for tag, attribute in attributes.items():
            schema = RootSchemaIndex.refuse_attribute_off_schema(
                database_entity.uid, tag, attribute, schemas.get(tag)
            )
            # Mapping items a mapper move removed are referred to by nothing.
            attribute = attribute.without_mapping_items(
                lambda uid: uid not in existing_mappings
            )
            self._attribute_service.set_display_value(attribute)
            database_attribute = self._database_service.add_attribute(
                session, attribute, schema
            )
            database_attribute.rejected = attribute.rejected
            database_attribute.read_only, database_attribute.locked = flags.get(
                attribute.uid, (False, False)
            )
            database_attributes.add(database_attribute)
        return database_attributes
