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

"""Running the migration of a project without saving it, and working out what
the curator has to resolve."""

import contextlib
import dataclasses
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from uuid import UUID

from slidetap.database import (
    DatabaseAttributeMigrationIssue,
    DatabaseMigrationEntity,
)
from slidetap.external_interfaces import SchemaMigration
from slidetap.model import (
    AnnotationSchema,
    AnyAttribute,
    AnyEntitySchema,
    AttributeSchema,
    Dataset,
    EntityMigrationResult,
    ImageSchema,
    Item,
    ItemSchema,
    MetadataSearchItem,
    MigrationError,
    NotAllowedActionError,
    ObservationSchema,
    Project,
    RootSchemaIndex,
    SampleSchema,
    UnresolvedAttributeMigration,
)
from slidetap.services.schema_service import SchemaService
from slidetap.services.validators.attribute_validator import AttributeValidator


@dataclass(frozen=True)
class EntityInMigration:
    """An entity of the project, and what the migration returned for it."""

    source: Project | Dataset | Item
    """The entity as it is on the source root."""

    target_schema: AnyEntitySchema
    """Its schema on the target root."""

    target_attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration]
    """Its attributes on the target schema by tag, each migrated, or
    unresolved for the curator to resolve."""

    target_private_attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration]
    """Its private attributes on the target schema, as `target_attributes`."""

    @property
    def identifier(self) -> str:
        """The name of the project or dataset, or the identifier of the item."""
        if isinstance(self.source, Item):
            return self.source.identifier
        return self.source.name

    @property
    def order(self) -> tuple[int, str]:
        """Where the entity goes among those of a migration: the project, the
        dataset, then the items by identifier."""
        if isinstance(self.source, Project):
            return 0, self.identifier
        if isinstance(self.source, Dataset):
            return 1, self.identifier
        return 2, self.identifier

    @property
    def migrated_attributes(self) -> dict[str, AnyAttribute]:
        """The migrated attributes on the target schema by tag, leaving out the
        unresolved."""
        return self._leave_out_unresolved(self.target_attributes)

    @property
    def migrated_private_attributes(self) -> dict[str, AnyAttribute]:
        """The migrated private attributes on the target schema by tag, leaving
        out the unresolved."""
        return self._leave_out_unresolved(self.target_private_attributes)

    @property
    def dropped_attributes(self) -> list[AnyAttribute]:
        """The attributes of the source entity with a value that the migration
        neither converted nor left unresolved."""
        kept = {
            attribute.uid
            for attribute in (
                *self.migrated_attributes.values(),
                *self.migrated_private_attributes.values(),
                *(
                    unresolved.original
                    for _, unresolved, _ in self.unresolved()
                    if unresolved.original is not None
                ),
            )
        }
        return [
            attribute
            for attribute in (
                *self.source.attributes.values(),
                *self.source.private_attributes.values(),
            )
            if attribute.uid not in kept and attribute.value is not None
        ]

    def unresolved(
        self,
    ) -> Iterator[tuple[str, UnresolvedAttributeMigration, AttributeSchema | None]]:
        """Iterate the unresolved attributes, public then private.

        Returns
        -------
        Iterator[tuple[str, UnresolvedAttributeMigration, AttributeSchema | None]]
            The tag and the unresolved attribute, with the attribute schema of
            the tag among the public or the private attributes of the target
            schema, as the attribute is, or None where it has none.
        """
        for attributes, schemas in (
            (self.target_attributes, self.target_schema.attributes),
            (self.target_private_attributes, self.target_schema.private_attributes),
        ):
            for tag, attribute in attributes.items():
                if isinstance(attribute, UnresolvedAttributeMigration):
                    yield tag, attribute, schemas.get(tag)

    @staticmethod
    def _leave_out_unresolved(
        attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration],
    ) -> dict[str, AnyAttribute]:
        """Leave out the unresolved attributes of a mapping by tag."""
        return {
            tag: attribute
            for tag, attribute in attributes.items()
            if not isinstance(attribute, UnresolvedAttributeMigration)
        }


@dataclass(frozen=True)
class SearchItemInMigration:
    """A search item of the project, and the item schema the migration moves it
    to."""

    source: MetadataSearchItem
    """The search item as it is on the source root."""

    target_schema: ItemSchema
    """Its item schema on the target root."""


@dataclass(frozen=True)
class ProjectMigrationPlan:
    """What the migration of a project returned, checked against the target
    root, and the attribute issues the curator resolves."""

    target_root: RootSchemaIndex
    """The root the project is migrated to."""

    entities: list[EntityInMigration]
    """The project, the dataset, and the items, in the order given, with every
    attribute that the migration left invalid, and that was valid before,
    unresolved."""

    search_items: list[SearchItemInMigration]
    """The search items, with their target item schemas."""

    attribute_issues: Mapping[UUID, list[DatabaseAttributeMigrationIssue]]
    """The attribute issues of each entity by its uid: one for each unresolved
    attribute and each dropped attribute."""


class ProjectMigrationPlanner:
    """Runs the migration of a root on the entities and search items of a
    project without saving anything, checks what it returns against the target
    root, and works out the attribute issues the curator resolves.

    An attribute issue is an attribute the migration left unresolved, a
    top-level attribute that was valid before and that the migration left
    invalid, or an attribute with a value that the migration dropped.
    """

    ITEM_SCHEMA_KINDS = (SampleSchema, ImageSchema, AnnotationSchema, ObservationSchema)

    def __init__(self, schema_service: SchemaService):
        """Create the planner.

        Parameters
        ----------
        schema_service: SchemaService
            For the roots and their migrations.
        """
        self._schema_service = schema_service

    def plan(
        self,
        source_root_schema_uid: UUID,
        target_root_schema_uid: UUID,
        entities: Iterable[Project | Dataset | Item],
        search_items: Iterable[MetadataSearchItem],
    ) -> ProjectMigrationPlan:
        """Run the migration of the source root for the entities of a project,
        on copies of them, check what it returns against the target root, pair
        the search items with the item schemas it moves them to, and work out
        the attribute issues.

        Parameters
        ----------
        source_root_schema_uid: UUID
            The uid of the root the project is on.
        target_root_schema_uid: UUID
            The uid of the root the project is migrated to.
        entities: Iterable[Project | Dataset | Item]
            The project, the dataset, and the items, on the source root.
        search_items: Iterable[MetadataSearchItem]
            The search items of the project, on the source root.

        Returns
        -------
        ProjectMigrationPlan
            The entities and the search items on the target root, and the
            attribute issues of each entity.

        Raises
        ------
        NotFoundError
            If there is no root of either uid.
        NotAllowedActionError
            If the source root has no migration.
        MigrationError
            If the migration returns what it may not.
        """
        source_root = self._schema_service.get_root(source_root_schema_uid)
        target_root = self._schema_service.get_root(target_root_schema_uid)
        migration = self._schema_service.migration_of(source_root_schema_uid)
        if migration is None:
            raise NotAllowedActionError(
                f"Root schema {source_root.display_name} has no migration."
            )
        entities_in_migration = [
            self._check_against_target_schema(
                source_root,
                target_root,
                self._pair_with_target_schema(
                    source_root,
                    target_root,
                    source,
                    self._migrate_entity_copy(migration, source),
                ),
            )
            for source in entities
        ]
        return ProjectMigrationPlan(
            target_root,
            entities_in_migration,
            [
                SearchItemInMigration(
                    search_item,
                    self._get_target_item_schema(
                        source_root,
                        target_root,
                        f"search item {search_item.uid}",
                        search_item.schema_uid,
                        migration.migrate_item_schema(
                            source_root.get_item(search_item.schema_uid)
                        ).uid,
                    ),
                )
                for search_item in search_items
            ],
            {
                entity.source.uid: list(
                    self._create_attribute_issues(source_root, target_root, entity)
                )
                for entity in entities_in_migration
            },
        )

    def refuse_changed_plan(
        self,
        plan: ProjectMigrationPlan,
        project_name: str,
        planned: Iterable[DatabaseMigrationEntity],
    ) -> None:
        """Refuse a migration that no longer leaves unresolved or drops what
        the stored plan has attribute issues of.

        Parameters
        ----------
        plan: ProjectMigrationPlan
            The migration of the project as it is planned now.
        project_name: str
            The name of the project, for the error.
        planned: Iterable[DatabaseMigrationEntity]
            The entities of the stored plan, with their attribute issues.

        Raises
        ------
        MigrationError
            If the attributes left unresolved or dropped are not those of the
            stored plan.
        """
        now = {
            self._get_issue_key(entity_uid, database_issue)
            for entity_uid, database_issues in plan.attribute_issues.items()
            for database_issue in database_issues
        }
        stored = {
            self._get_issue_key(database_entity.entity_uid, database_issue)
            for database_entity in planned
            for database_issue in database_entity.attribute_issues
        }
        if now != stored:
            raise MigrationError(
                f"The migration of project {project_name} no longer leaves "
                f"unresolved or drops what was planned: {len(now - stored)} "
                f"attributes are unresolved or dropped that are not in the plan, "
                f"and {len(stored - now)} in the plan are no longer. Revert "
                f"the migration and start it again."
            )

    @staticmethod
    def _get_issue_key(
        entity_uid: UUID, database_issue: DatabaseAttributeMigrationIssue
    ) -> tuple[UUID, UUID | None, UUID | None]:
        """Get what an attribute issue is about: the entity, and the target
        attribute schema, or the source attribute schema of a dropped one.

        Parameters
        ----------
        entity_uid: UUID
            The uid of the entity of the attribute issue.
        database_issue: DatabaseAttributeMigrationIssue
            The attribute issue.

        Returns
        -------
        tuple[UUID, UUID | None, UUID | None]
            The uid of the entity, of the target attribute schema, and of the
            source attribute schema where the attribute is dropped.
        """
        return (
            entity_uid,
            database_issue.target_attribute_schema_uid,
            database_issue.source_attribute_schema_uid
            if database_issue.dropped
            else None,
        )

    @staticmethod
    def _migrate_entity_copy(
        migration: SchemaMigration, source: Project | Dataset | Item
    ) -> EntityMigrationResult:
        """Run the migration for an entity, on a copy of it.

        Parameters
        ----------
        migration: SchemaMigration
            The migration of the source root.
        source: Project | Dataset | Item
            The entity, on the source root.

        Returns
        -------
        EntityMigrationResult
            What the migration returned for the entity.
        """
        copy = source.model_copy(deep=True)
        if isinstance(copy, Project):
            return migration.migrate_project(copy)
        if isinstance(copy, Dataset):
            return migration.migrate_dataset(copy)
        return migration.migrate_item(copy)

    def _pair_with_target_schema(
        self,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
        source: Project | Dataset | Item,
        migrated: EntityMigrationResult,
    ) -> EntityInMigration:
        """Pair an entity with what the migration returned for it, on the
        target schema the migration put it on.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the project is on.
        target_root: RootSchemaIndex
            The root the project is migrated to.
        source: Project | Dataset | Item
            The entity, on the source root.
        migrated: EntityMigrationResult
            What the migration returned for the entity.

        Returns
        -------
        EntityInMigration
            The entity, with the target schema and what the migration returned.

        Raises
        ------
        MigrationError
            If the target schema is not the project or the dataset schema of
            the target root for the project or the dataset, or not an item
            schema of the target root of the same kind for an item.
        """
        if isinstance(source, Project | Dataset):
            target_schema: AnyEntitySchema = (
                target_root.project
                if isinstance(source, Project)
                else target_root.dataset
            )
            if migrated.schema_uid != target_schema.uid:
                raise MigrationError(
                    f"The migration put {source.uid} on schema "
                    f"{migrated.schema_uid}, not on {target_schema.uid} of the "
                    f"target root."
                )
        else:
            target_schema = self._get_target_item_schema(
                source_root,
                target_root,
                f"item {source.uid}",
                source.schema_uid,
                migrated.schema_uid,
            )
        return EntityInMigration(
            source,
            target_schema,
            migrated.attributes,
            migrated.private_attributes,
        )

    def _get_target_item_schema(
        self,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
        name: str,
        source_schema_uid: UUID,
        target_schema_uid: UUID,
    ) -> ItemSchema:
        """Get the item schema of the target root an item or a search item is
        migrated to, which must be of the kind of its source schema.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the project is on.
        target_root: RootSchemaIndex
            The root the project is migrated to.
        name: str
            What it is, for the error.
        source_schema_uid: UUID
            The uid of its source schema.
        target_schema_uid: UUID
            The uid of the target schema the migration put it on.

        Returns
        -------
        ItemSchema
            The target schema.

        Raises
        ------
        MigrationError
            If the target root has no item schema of the uid, or one of
            another kind.
        """
        source_schema = source_root.items.get(source_schema_uid)
        target_schema = target_root.items.get(target_schema_uid)
        if target_schema is None or not any(
            isinstance(source_schema, kind) and isinstance(target_schema, kind)
            for kind in self.ITEM_SCHEMA_KINDS
        ):
            raise MigrationError(
                f"The migration put {name} on schema {target_schema_uid}, which "
                f"is not an item schema of the same kind in the target root."
            )
        return target_schema

    def _check_against_target_schema(
        self,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
        entity: EntityInMigration,
    ) -> EntityInMigration:
        """Refuse what the migration returned off the target schema, and leave
        unresolved what it left invalid that was valid.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the project is on.
        target_root: RootSchemaIndex
            The root the project is migrated to.
        entity: EntityInMigration
            The entity, as the migration returned it.

        Returns
        -------
        EntityInMigration
            The entity, with every attribute that the migration left invalid,
            and that was valid before, unresolved.

        Raises
        ------
        MigrationError
            If an attribute is not the target schema's by tag, or an unresolved
            attribute is not a tag of the target schema, among the public or
            the private attributes as it is, or is proposed on another
            attribute schema.
        """
        uid, target_schema = entity.source.uid, entity.target_schema
        for attributes, schemas in (
            (entity.migrated_attributes, target_schema.attributes),
            (entity.migrated_private_attributes, target_schema.private_attributes),
        ):
            for tag, attribute in attributes.items():
                RootSchemaIndex.refuse_attribute_off_schema(
                    uid, tag, attribute, schemas.get(tag)
                )
        for tag, unresolved, attribute_schema in entity.unresolved():
            if attribute_schema is None:
                raise MigrationError(
                    f"The migration left {tag!r} of {uid} unresolved, which "
                    f"is not an attribute of the target schema."
                )
            if unresolved.proposed is not None:
                RootSchemaIndex.refuse_attribute_off_schema(
                    uid, tag, unresolved.proposed, attribute_schema
                )
        return self._unresolve_invalidated_attributes(source_root, target_root, entity)

    def _unresolve_invalidated_attributes(
        self,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
        entity: EntityInMigration,
    ) -> EntityInMigration:
        """Leave unresolved every top-level attribute that the migration left
        invalid, and that was valid before: one newly required and without a
        value, or one whose value is not valid on the target schema. One that
        was invalid before is left as it is.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the project is on.
        target_root: RootSchemaIndex
            The root the project is migrated to.
        entity: EntityInMigration
            The entity, as the migration returned it.

        Returns
        -------
        EntityInMigration
            The entity, with those attributes unresolved.
        """
        source_schema = source_root.get_entity_schema(entity.source.schema_uid)
        attributes = dict(entity.target_attributes)
        for tag, target_attribute_schema in entity.target_schema.attributes.items():
            attribute = attributes.get(tag)
            if isinstance(attribute, UnresolvedAttributeMigration):
                continue
            if self._is_attribute_valid(attribute, target_attribute_schema):
                continue
            source_tag, original = self._get_original_attribute(
                entity.source, attribute, tag
            )
            source_attribute_schema = source_schema.attributes.get(source_tag)
            if source_attribute_schema is not None and not self._is_attribute_valid(
                original, source_attribute_schema
            ):
                continue
            attributes[tag] = UnresolvedAttributeMigration(
                original=original,
                proposed=attribute,
                problem=(
                    f"Required in {target_root.display_name}, has no value."
                    if attribute is None or attribute.value is None
                    else f"Not a valid value in {target_root.display_name}."
                ),
            )
        return dataclasses.replace(entity, target_attributes=attributes)

    def _create_attribute_issues(
        self,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
        entity: EntityInMigration,
    ) -> Iterator[DatabaseAttributeMigrationIssue]:
        """Make the attribute issues of what an entity left unresolved, and of
        what it dropped.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the project is on.
        target_root: RootSchemaIndex
            The root the project is migrated to.
        entity: EntityInMigration
            The entity, checked.

        Returns
        -------
        Iterator[DatabaseAttributeMigrationIssue]
            An attribute issue for each unresolved attribute and each dropped
            attribute, with the original given its display value.

        Raises
        ------
        MigrationError
            If an unresolved attribute is not a tag of the target schema.
        """
        for tag, unresolved, schema in entity.unresolved():
            original = None
            if unresolved.original is not None:
                original = unresolved.original.model_copy(deep=True)
                self._set_display_value(source_root, original)
            if schema is None:
                raise MigrationError(
                    f"The migration left {tag!r} of {entity.source.uid} "
                    f"unresolved, which is not an attribute of the target schema."
                )
            yield DatabaseAttributeMigrationIssue(
                original.schema_uid if original is not None else None,
                schema.uid,
                original,
                unresolved.proposed,
                unresolved.problem,
            )
        for attribute in entity.dropped_attributes:
            original = attribute.model_copy(deep=True)
            self._set_display_value(source_root, original)
            schema = self._get_source_attribute_schema(source_root, original.schema_uid)
            display_name = (
                schema.display_name if schema is not None else str(original.schema_uid)
            )
            value = original.display_value
            dropped = display_name if value is None else f"'{value}' of {display_name}"
            yield DatabaseAttributeMigrationIssue(
                original.schema_uid,
                None,
                original,
                None,
                f"{dropped} is dropped: it has no place in {target_root.display_name}.",
            )

    @staticmethod
    def _get_original_attribute(
        source: Project | Dataset | Item, attribute: AnyAttribute | None, tag: str
    ) -> tuple[str, AnyAttribute | None]:
        """Get the attribute of the source entity a migrated attribute was.

        Parameters
        ----------
        source: Project | Dataset | Item
            The entity, on the source root.
        attribute: AnyAttribute | None
            The migrated attribute, or None where there is none.
        tag: str
            The target tag of the migrated attribute.

        Returns
        -------
        tuple[str, AnyAttribute | None]
            The source tag and the attribute of the same uid, else the tag and
            the attribute of the source entity at it, None where it has none.
        """
        if attribute is not None:
            for source_tag, original in source.attributes.items():
                if original.uid == attribute.uid:
                    return source_tag, original
        return tag, source.attributes.get(tag)

    @staticmethod
    def _is_attribute_valid(
        attribute: AnyAttribute | None, schema: AttributeSchema
    ) -> bool:
        """Check if an attribute is valid on an attribute schema.

        Parameters
        ----------
        attribute: AnyAttribute | None
            The attribute, or None where there is none.
        schema: AttributeSchema
            The attribute schema.

        Returns
        -------
        bool
            Whether the attribute is valid, or None is, as the schema is
            optional.
        """
        if attribute is None:
            return schema.optional
        return AttributeValidator.validate_attribute(
            attribute.model_copy(deep=True), schema
        )

    @staticmethod
    def _get_source_attribute_schema(
        source_root: RootSchemaIndex, attribute_schema_uid: UUID
    ) -> AttributeSchema | None:
        """Get an attribute schema of the source root, public or private.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the project is on.
        attribute_schema_uid: UUID
            The uid of the attribute schema.

        Returns
        -------
        AttributeSchema | None
            The attribute schema, or None where the source root has none of
            the uid.
        """
        return source_root.attributes.get(
            attribute_schema_uid
        ) or source_root.private_attributes.get(attribute_schema_uid)

    def _set_display_value(
        self, source_root: RootSchemaIndex, attribute: AnyAttribute
    ) -> None:
        """Set the display value of an attribute of the source root, where its
        schema is known.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the project is on.
        attribute: AnyAttribute
            The attribute, given its display value.
        """
        schema = self._get_source_attribute_schema(source_root, attribute.schema_uid)
        if schema is None:
            return
        if attribute.value is None:
            attribute.display_value = None
            return
        with contextlib.suppress(KeyError, ValueError):
            attribute.display_value = schema.create_display_value(attribute.value)
