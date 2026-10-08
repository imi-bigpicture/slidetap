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

"""A schema migration of entity migrators and attribute migrators."""

from collections.abc import Collection, Iterable
from typing import cast
from uuid import UUID

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeMigrator,
    UnchangedAttributeMigrator,
)
from slidetap.external_interfaces.implementations.migration.attribute_migrators import (
    AttributeMigrators,
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
    RootSchemaIndex,
)


class RootSchemaMigration(SchemaMigration):
    """Moves projects from a source root to a target root with the entity
    migrators given: one of the project and of the dataset, where they change,
    and one of each item schema whose items change.

    The project or dataset without a migrator is returned as the same on the
    target root. The items of the item schemas with a migrator are the
    migrated item schemas; any other item schema must be the same in the target
    root.

    The attribute of a mapping item, and the target of an attribute schema, are
    given by the attribute migrators registered for the source attribute
    schema. An attribute schema not registered that the target root has under
    the same uid, the same schema, is moved there as it is.
    """

    def __init__(
        self,
        source_schema: RootSchema,
        target_schema: RootSchema,
        attribute_migrators: AttributeMigrators,
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
        attribute_migrators: AttributeMigrators
            The attribute migrators of the attribute schemas that change.
        project_migrator: EntityMigrator[Project] | None = None
            The migrator of the project, None where it does not change.
        dataset_migrator: EntityMigrator[Dataset] | None = None
            The migrator of the dataset, None where it does not change.
        item_migrators: Iterable[EntityMigrator[Item]] = ()
            The migrators of the items of the item schemas that change, each of
            its source item schema.

        Raises
        ------
        ValueError
            If two item migrators are of the same source item schema.
        """
        self._source_schema = source_schema
        self._target_root = RootSchemaIndex(target_schema, is_default=False)
        self._attribute_migrators = attribute_migrators
        self._project_migrator = project_migrator
        self._dataset_migrator = dataset_migrator
        self._item_migrators: dict[UUID, EntityMigrator[Item]] = {}
        for migrator in item_migrators:
            if migrator.source.uid in self._item_migrators:
                raise ValueError(
                    f"Two migrators are given for item schema "
                    f"{migrator.source.name} ({migrator.source.uid})."
                )
            self._item_migrators[migrator.source.uid] = migrator
        self._unchanged = UnchangedAttributeMigrator()

    @property
    def attribute_migrators(self) -> AttributeMigrators:
        """The attribute migrators of the attribute schemas that change."""
        return self._attribute_migrators

    @property
    def migrated_item_schemas(self) -> Collection[UUID]:
        """The uids of the source item schemas with an item migrator."""
        return self._item_migrators.keys()

    def migrate_project(self, project: Project) -> EntityMigrationResult | None:
        """Migrate a project with the project migrator.

        Parameters
        ----------
        project: Project
            The project, on the project schema of the source root.

        Returns
        -------
        EntityMigrationResult | None
            What the project migrator returns, or None without one.
        """
        if self._project_migrator is None:
            return None
        return self._project_migrator.migrate(project)

    def migrate_dataset(self, dataset: Dataset) -> EntityMigrationResult | None:
        """Migrate a dataset with the dataset migrator.

        Parameters
        ----------
        dataset: Dataset
            The dataset, on the dataset schema of the source root.

        Returns
        -------
        EntityMigrationResult | None
            What the dataset migrator returns, or None without one.
        """
        if self._dataset_migrator is None:
            return None
        return self._dataset_migrator.migrate(dataset)

    def migrate_item(self, item: Item) -> EntityMigrationResult | None:
        """Migrate an item with the migrator of its item schema.

        Parameters
        ----------
        item: Item
            The item, on a migrated item schema.

        Returns
        -------
        EntityMigrationResult | None
            What the migrator of its item schema returns.

        Raises
        ------
        ValueError
            If the item is not on a migrated item schema.
        """
        return self._item_migrator(item.schema_uid).migrate(item)

    def migrate_item_schema(self, schema: ItemSchema) -> ItemSchema:
        """Give the target item schema of the migrator of a source item schema.

        Parameters
        ----------
        schema: ItemSchema
            A migrated item schema.

        Returns
        -------
        ItemSchema
            The target item schema of its migrator.

        Raises
        ------
        ValueError
            If the schema is not a migrated item schema.
        """
        return cast(ItemSchema, self._item_migrator(schema.uid).target)

    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        """Migrate the attribute of a mapping item with the migrator registered
        for its schema, or move it as it is to the same schema in the target.

        An attribute whose value has no counterpart on the target schema is
        returned without it.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute, on an attribute schema of the source root.

        Returns
        -------
        AnyAttribute | None
            The attribute on the target attribute schema, or None where its
            schema is neither registered nor in the target root.
        """
        found = self._find(attribute.schema_uid)
        if found is None:
            return None
        migrator, target = found
        return migrator.migrate(attribute, target).attribute

    def migrate_attribute_schema(
        self, schema: AttributeSchema
    ) -> AttributeSchema | None:
        """Give the target of the migrator registered for an attribute schema,
        or the same schema where the target root has it.

        Parameters
        ----------
        schema: AttributeSchema
            An attribute schema of the source root.

        Returns
        -------
        AttributeSchema | None
            The target attribute schema, or None where the schema is neither
            registered nor in the target root.
        """
        found = self._find(schema.uid)
        return None if found is None else found[1]

    def _item_migrator(self, schema_uid: UUID) -> EntityMigrator[Item]:
        """Get the migrator of a migrated item schema.

        Raises
        ------
        ValueError
            If the item schema has no migrator.
        """
        migrator = self._item_migrators.get(schema_uid)
        if migrator is None:
            raise ValueError(
                f"Item schema {schema_uid} is not migrated by the migration of "
                f"root {self._source_schema.name}."
            )
        return migrator

    def _find(
        self, schema_uid: UUID
    ) -> tuple[AttributeMigrator, AttributeSchema] | None:
        """Find the migrator and target of a source attribute schema: the
        registered ones, else moving it as it is to the same schema in the
        target root, else None."""
        registered = self._attribute_migrators.get(schema_uid)
        if registered is not None:
            return registered
        target = self._target_root.attributes.get(
            schema_uid
        ) or self._target_root.private_attributes.get(schema_uid)
        if target is None:
            return None
        return self._unchanged, target
