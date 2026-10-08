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

"""A schema migration of entity migrators."""

from collections.abc import Iterable
from typing import Any, cast
from uuid import UUID

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeMigrator,
)
from slidetap.external_interfaces.implementations.migration.entity_migrator import (
    EntityMigrator,
)
from slidetap.external_interfaces.schema_migration import SchemaMigration
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    EntityMigrationResult,
    Item,
    ItemSchema,
    Project,
    RootSchema,
)


class DeclarativeSchemaMigration(SchemaMigration):
    """Moves projects from a source root to a target root with an
    `EntityMigrator` for the project, the dataset, and each item schema of the
    source.

    A migrator not given is a plain `EntityMigrator`, which declares nothing:
    for the project and the dataset, and for an item schema of the source that
    the target has under the same uid. An item schema of the source with
    neither a migrator nor such a target is refused.

    The attribute migrators of the entity migrators, at any depth, are
    registered by their source attribute schema when the migration is created;
    one held in several places must be migrated alike in each. With them,
    `migrate_attribute` migrates an attribute, so that the mapping items of a
    mapper moved to the target root are migrated as the attributes of the
    entities are, and `migrate_attribute_schema` gives the target schema of an
    attribute schema. `migrate_item_schema` gives the target item schema of the
    migrator of an item schema.
    """

    def __init__(
        self,
        source_schema: RootSchema,
        target_schema: RootSchema,
        project_migrator: EntityMigrator[Project] | None = None,
        dataset_migrator: EntityMigrator[Dataset] | None = None,
        item_migrators: Iterable[EntityMigrator[Item]] = (),
    ):
        """Create the migration between two roots.

        Parameters
        ----------
        source_schema: RootSchema
            The root schema the projects are moved from.
        target_schema: RootSchema
            The root schema the projects are moved to.
        project_migrator: EntityMigrator[Project] | None = None
            The migrator of the project.
        dataset_migrator: EntityMigrator[Dataset] | None = None
            The migrator of the dataset.
        item_migrators: Iterable[EntityMigrator[Item]] = ()
            The migrators of the items, each of its source item schema.

        Raises
        ------
        ValueError
            If an item schema of the source has neither a migrator nor an item
            schema of the same uid in the target, a migrator is given for an
            item schema that is not of the source or that already has one, a
            plain migrator created here says nothing about an attribute it
            cannot move as it is, or an attribute schema is migrated
            differently in two places.
        """
        self._source_schema = source_schema
        self._target_schema = target_schema
        self._project_migrator = (
            EntityMigrator[Project](source_schema.project, target_schema.project)
            if project_migrator is None
            else project_migrator
        )
        self._dataset_migrator = (
            EntityMigrator[Dataset](source_schema.dataset, target_schema.dataset)
            if dataset_migrator is None
            else dataset_migrator
        )
        self._item_migrators = self._create_item_migrators(item_migrators)
        self._attribute_migrators = self._register_attribute_migrators(
            [
                self._project_migrator,
                self._dataset_migrator,
                *self._item_migrators.values(),
            ]
        )

    def migrate_project(self, project: Project) -> EntityMigrationResult:
        """Migrate a project from its schema on the source root to the target
        root, with the project migrator.

        Parameters
        ----------
        project: Project
            The project, on the project schema of the source root.

        Returns
        -------
        EntityMigrationResult
            The project schema of the target root, the project's attributes on
            it, and the attributes that lost values as unresolved.
        """
        return self._project_migrator.migrate(project)

    def migrate_dataset(self, dataset: Dataset) -> EntityMigrationResult:
        """Migrate a dataset from its schema on the source root to the target
        root, with the dataset migrator.

        Parameters
        ----------
        dataset: Dataset
            The dataset, on the dataset schema of the source root.

        Returns
        -------
        EntityMigrationResult
            The dataset schema of the target root, the dataset's attributes on
            it, and the attributes that lost values as unresolved.
        """
        return self._dataset_migrator.migrate(dataset)

    def migrate_item(self, item: Item) -> EntityMigrationResult:
        """Migrate an item from its schema on the source root to the target root,
        with the migrator of its item schema.

        Parameters
        ----------
        item: Item
            The item, on an item schema of the source root.

        Returns
        -------
        EntityMigrationResult
            The target item schema of the migrator, the item's attributes on
            it, and the attributes that lost values as unresolved.

        Raises
        ------
        ValueError
            If the item is not on an item schema of the source root.
        """
        migrator = self._item_migrators.get(item.schema_uid)
        if migrator is None:
            raise ValueError(
                f"Item {item.uid} is of schema {item.schema_uid}, which is not an "
                f"item schema of root {self._source_schema.name}."
            )
        return migrator.migrate(item)

    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        """Migrate the attribute of a mapping item with the attribute migrator
        of its schema, at any depth of an entity migrator.

        An attribute whose value has no counterpart on the target schema is
        returned without it.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute, on an attribute schema of the source root.

        Returns
        -------
        AnyAttribute | None
            The attribute on the target attribute schema, or None where no
            entity migrator has a migrator of its schema.
        """
        found = self._attribute_migrators.get(attribute.schema_uid)
        if found is None:
            return None
        migrator, target = found
        return migrator.migrate(attribute, target).attribute

    def migrate_item_schema(self, schema: ItemSchema) -> ItemSchema:
        """Give the target item schema of the migrator of a source item schema.

        Parameters
        ----------
        schema: ItemSchema
            An item schema of the source root.

        Returns
        -------
        ItemSchema
            The target item schema of the migrator.

        Raises
        ------
        ValueError
            If the schema is not an item schema of the source root.
        """
        migrator = self._item_migrators.get(schema.uid)
        if migrator is None:
            raise ValueError(
                f"Item schema {schema.name} ({schema.uid}) is not an item schema "
                f"of root {self._source_schema.name}."
            )
        return cast(ItemSchema, migrator.target)

    def migrate_attribute_schema(
        self, schema: AttributeSchema
    ) -> AttributeSchema | None:
        """Give the target attribute schema of the attribute migrator of a
        source attribute schema, at any depth of an entity migrator.

        Parameters
        ----------
        schema: AttributeSchema
            An attribute schema of the source root.

        Returns
        -------
        AttributeSchema | None
            The target attribute schema, or None where no entity migrator has a
            migrator of the schema.
        """
        found = self._attribute_migrators.get(schema.uid)
        return None if found is None else found[1]

    def _create_item_migrators(
        self, declared: Iterable[EntityMigrator[Item]]
    ) -> dict[UUID, EntityMigrator[Item]]:
        """Index the declared migrators by the uid of their source item schema,
        adding a plain one for every other item schema of the source, to the
        item schema of the same uid in the target.

        Raises
        ------
        ValueError
            If two migrators are given for an item schema, one is given for an
            item schema not of the source, or an item schema of the source has
            neither a migrator nor an item schema of the same uid in the
            target.
        """
        source_items = self._item_schemas(self._source_schema)
        target_items = self._item_schemas(self._target_schema)
        by_source: dict[UUID, EntityMigrator[Item]] = {}
        for migrator in declared:
            if migrator.source.uid in by_source:
                raise ValueError(
                    f"Two migrators are given for item schema "
                    f"{migrator.source.name} ({migrator.source.uid})."
                )
            by_source[migrator.source.uid] = migrator
        migrators: dict[UUID, EntityMigrator[Item]] = {}
        for uid, source_item in source_items.items():
            migrator = by_source.get(uid)
            if migrator is not None:
                migrators[uid] = migrator
                continue
            target_item = target_items.get(uid)
            if target_item is None:
                raise ValueError(
                    f"Item schema {source_item.name} ({uid}) of root "
                    f"{self._source_schema.name} has no migrator, and no item schema "
                    f"of the same uid in root {self._target_schema.name}."
                )
            migrators[uid] = EntityMigrator[Item](source_item, target_item)
        unknown = by_source.keys() - source_items.keys()
        if unknown:
            raise ValueError(
                f"Migrators are given for {', '.join(map(str, unknown))}, which "
                f"are not item schemas of root {self._source_schema.name}."
            )
        return migrators

    @staticmethod
    def _register_attribute_migrators(
        entity_migrators: Iterable[EntityMigrator[Any]],
    ) -> dict[UUID, tuple[AttributeMigrator, AttributeSchema]]:
        """Index the attribute migrators of the entity migrators, at any depth,
        by the uid of their source attribute schema.

        An attribute schema held in several places, such as one shared by item
        schemas, is registered once where every place migrates it alike: to
        the same target attribute schema, with equal migrators.

        Parameters
        ----------
        entity_migrators: Iterable[EntityMigrator[Any]]
            The migrators of the project, the dataset, and the items.

        Returns
        -------
        dict[UUID, tuple[AttributeMigrator, AttributeSchema]]
            The migrator of each source attribute schema, and the target
            attribute schema it migrates to.

        Raises
        ------
        ValueError
            If an attribute schema is migrated differently in two places.
        """
        registry: dict[UUID, tuple[AttributeMigrator, AttributeSchema]] = {}
        registered_by: dict[UUID, EntityMigrator[Any]] = {}
        conflicts: dict[UUID, str] = {}
        for entity_migrator in entity_migrators:
            for uid, migrator, target in entity_migrator.attribute_migrators():
                registered = registry.get(uid)
                if registered is None:
                    registry[uid] = (migrator, target)
                    registered_by[uid] = entity_migrator
                    continue
                registered_migrator, registered_target = registered
                if registered_target.uid == target.uid and (
                    registered_migrator == migrator
                ):
                    continue
                conflicts.setdefault(
                    uid,
                    f"{uid}, by the migrators of "
                    f"{registered_by[uid].source.name} (to {registered_target.tag} "
                    f"({registered_target.uid}) with "
                    f"{type(registered_migrator).__name__}) and "
                    f"{entity_migrator.source.name} (to {target.tag} ({target.uid}) "
                    f"with {type(migrator).__name__})",
                )
        if conflicts:
            raise ValueError(
                f"Attribute schemas are migrated differently in two places: "
                f"{'; '.join(conflicts.values())}."
            )
        return registry

    @staticmethod
    def _item_schemas(root: RootSchema) -> dict[UUID, ItemSchema]:
        """Collect the item schemas of a root by uid."""
        return {
            **root.samples,
            **root.images,
            **root.observations,
            **root.annotations,
        }
