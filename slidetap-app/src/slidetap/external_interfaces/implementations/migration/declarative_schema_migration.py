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

"""A schema migration of object migrators."""

from collections.abc import Iterable, Sequence
from typing import Any
from uuid import UUID

from slidetap.external_interfaces.implementations.migration.object_migrator import (
    ObjectMigrator,
)
from slidetap.external_interfaces.schema_migration import SchemaMigration
from slidetap.model import (
    AnyAttribute,
    Dataset,
    Item,
    ItemSchema,
    MetadataSearchItem,
    MigratedObject,
    Project,
    RootSchema,
)


class DeclarativeSchemaMigration(SchemaMigration):
    """Moves projects from a source root to a target root with an
    `ObjectMigrator` for the project, the dataset, and each item schema of the
    source.

    A migrator not given is a plain `ObjectMigrator`, which declares nothing:
    for the project and the dataset, and for an item schema of the source that
    the target has under the same uid. An item schema of the source with
    neither a migrator nor such a target is refused.

    `migrate_attribute` migrates an attribute with the migrator whose schemas
    hold it, at any depth, so that the mapping items of a mapper moved to the
    target root are migrated as the attributes of the objects are.
    """

    def __init__(
        self,
        source: RootSchema,
        target: RootSchema,
        project_migrator: ObjectMigrator[Project] | None = None,
        dataset_migrator: ObjectMigrator[Dataset] | None = None,
        item_migrators: Iterable[ObjectMigrator[Item]] = (),
    ):
        """Create the migration between two roots.

        Parameters
        ----------
        source: RootSchema
            The root the projects are moved from.
        target: RootSchema
            The root the projects are moved to.
        project_migrator: ObjectMigrator[Project] | None = None
            The migrator of the project.
        dataset_migrator: ObjectMigrator[Dataset] | None = None
            The migrator of the dataset.
        item_migrators: Iterable[ObjectMigrator[Item]] = ()
            The migrators of the items, each of its source item schema.

        Raises
        ------
        ValueError
            If an item schema of the source has neither a migrator nor an item
            schema of the same uid in the target, a migrator is given for an
            item schema that is not of the source or that already has one, or a
            plain migrator created here says nothing about an attribute it
            cannot move as it is.
        """
        self._source = source
        self._target = target
        self._project_migrator = (
            ObjectMigrator[Project](source.project, target.project)
            if project_migrator is None
            else project_migrator
        )
        self._dataset_migrator = (
            ObjectMigrator[Dataset](source.dataset, target.dataset)
            if dataset_migrator is None
            else dataset_migrator
        )
        self._item_migrators = self._create_item_migrators(item_migrators)

    @property
    def source(self) -> RootSchema:
        return self._source

    @property
    def target(self) -> RootSchema:
        return self._target

    @property
    def project_migrator(self) -> ObjectMigrator[Project]:
        return self._project_migrator

    @property
    def dataset_migrator(self) -> ObjectMigrator[Dataset]:
        return self._dataset_migrator

    @property
    def item_migrators(self) -> Sequence[ObjectMigrator[Item]]:
        """The migrators of the items, one for each item schema of the
        source."""
        return list(self._item_migrators.values())

    @property
    def migrators(self) -> list[ObjectMigrator[Any]]:
        """Every migrator: of the project, the dataset, and the items."""
        return [
            self._project_migrator,
            self._dataset_migrator,
            *self._item_migrators.values(),
        ]

    def migrate_project(self, project: Project) -> MigratedObject:
        return self._project_migrator.migrate(project)

    def migrate_dataset(self, dataset: Dataset) -> MigratedObject:
        return self._dataset_migrator.migrate(dataset)

    def migrate_item(self, item: Item) -> MigratedObject:
        return self._item_migrator(f"Item {item.uid}", item.schema_uid).migrate(item)

    def migrate_search_item(self, search_item: MetadataSearchItem) -> UUID:
        """The target item schema of the migrator of the item schema of the
        search item."""
        return self._item_migrator(
            f"Search item {search_item.uid}", search_item.schema_uid
        ).target.uid

    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        """The attribute migrated by the attribute migrator of its schema, at
        any depth of an object migrator, or None where it has none.

        An attribute whose value has no counterpart on the target schema is
        returned without it."""
        for migrator in self.migrators:
            found = migrator.attribute_migrator_of(attribute.schema_uid)
            if found is not None:
                attribute_migrator, target = found
                return attribute_migrator.migrate(attribute, target).attribute
        return None

    def _item_migrator(self, name: str, schema_uid: UUID) -> ObjectMigrator[Item]:
        """The migrator of an item schema of the source root, for an item or a
        search item as named.

        Raises
        ------
        ValueError
            If the schema is not an item schema of the source root.
        """
        migrator = self._item_migrators.get(schema_uid)
        if migrator is None:
            raise ValueError(
                f"{name} is of schema {schema_uid}, which is not an item schema of "
                f"root {self._source.name}."
            )
        return migrator

    def _create_item_migrators(
        self, declared: Iterable[ObjectMigrator[Item]]
    ) -> dict[UUID, ObjectMigrator[Item]]:
        """The declared migrators, and a plain one for every other item schema
        of the source, to the item schema of the same uid in the target, by the
        uid of their source item schema."""
        source_items = self._item_schemas(self._source)
        target_items = self._item_schemas(self._target)
        by_source: dict[UUID, ObjectMigrator[Item]] = {}
        for migrator in declared:
            if migrator.source.uid in by_source:
                raise ValueError(
                    f"Two migrators are given for item schema "
                    f"{migrator.source.name} ({migrator.source.uid})."
                )
            by_source[migrator.source.uid] = migrator
        migrators: dict[UUID, ObjectMigrator[Item]] = {}
        for uid, source_item in source_items.items():
            migrator = by_source.get(uid)
            if migrator is not None:
                migrators[uid] = migrator
                continue
            target_item = target_items.get(uid)
            if target_item is None:
                raise ValueError(
                    f"Item schema {source_item.name} ({uid}) of root "
                    f"{self._source.name} has no migrator, and no item schema of "
                    f"the same uid in root {self._target.name}."
                )
            migrators[uid] = ObjectMigrator[Item](source_item, target_item)
        unknown = by_source.keys() - source_items.keys()
        if unknown:
            raise ValueError(
                f"Migrators are given for {', '.join(map(str, unknown))}, which "
                f"are not item schemas of root {self._source.name}."
            )
        return migrators

    @staticmethod
    def _item_schemas(root: RootSchema) -> dict[UUID, ItemSchema]:
        return {
            **root.samples,
            **root.images,
            **root.observations,
            **root.annotations,
        }
