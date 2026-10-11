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

"""Interface for moving projects from one root schema to another."""

from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from uuid import UUID

from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    EntityMigrationResult,
    Item,
    ItemSchema,
    Project,
)


class SchemaMigration(metaclass=ABCMeta):
    """Migrates projects, datasets, and items from a previous root schema to the
    root of new projects, one entity at a time, and gives the schemas of the
    target root that schemas of the source migrate to.

    Each method that migrates an entity returns what it is on the target root,
    or None where the entity is the same there, which it may only be where its
    schema is the same in the target root, under the same uid. What a
    migration cannot migrate by itself it returns as an
    `UnresolvedAttributeMigration`, for a curator to decide; it is then run
    again to complete the migration, and must return the same.
    Changes across entities are not supported.

    Only the items on `migrated_item_schemas` are given to the migration; every
    other item schema must be the same in the target root, and its items are
    left as they are. The project and the dataset are always given.

    The attribute migrators of `slidetap.external_interfaces.implementations`,
    such as `EnumAttributeMigrator`, migrate an attribute for an implementation.
    """

    @property
    @abstractmethod
    def migrated_item_schemas(self) -> Collection[UUID]:
        """The uids of the item schemas of the source root whose items the
        migration migrates.

        Every other item schema of the source root is checked to be the same,
        under the same uid, in the target root when the migration is loaded.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_project(self, project: Project) -> EntityMigrationResult | None:
        """Migrate a project from its schema on the source root to the target root.

        Parameters
        ----------
        project: Project
            The project, on the project schema of the source root.

        Returns
        -------
        EntityMigrationResult | None
            The project schema of the target root, the project's attributes on
            it, and an `UnresolvedAttributeMigration` for each attribute that
            needs a curator's decision, or None where the project is the same
            on the target root.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_dataset(self, dataset: Dataset) -> EntityMigrationResult | None:
        """Migrate a dataset from its schema on the source root to the target root.

        Parameters
        ----------
        dataset: Dataset
            The dataset, on the dataset schema of the source root.

        Returns
        -------
        EntityMigrationResult | None
            The dataset schema of the target root, the dataset's attributes on
            it, and an `UnresolvedAttributeMigration` for each attribute that
            needs a curator's decision, or None where the dataset is the same
            on the target root.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_item(self, item: Item) -> EntityMigrationResult | None:
        """Migrate an item from its schema on the source root to the target root.

        Parameters
        ----------
        item: Item
            The item: a sample, image, annotation, or observation, on an item
            schema of the source root that is one of `migrated_item_schemas`.

        Returns
        -------
        EntityMigrationResult | None
            The item schema of the target root, of the same kind, the item's
            attributes on it, and an `UnresolvedAttributeMigration` for each
            attribute that needs a curator's decision, or None where the item
            is the same on the target root.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        """Migrate an attribute of a mapping item to the target root.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute, on an attribute schema of the source root, at any
            depth.

        Returns
        -------
        AnyAttribute | None
            The attribute on the attribute schema of the target root it moves
            to, or None where it has none.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_item_schema(self, schema: ItemSchema) -> ItemSchema:
        """Give the item schema of the target root that a source item schema
        migrates to.

        Parameters
        ----------
        schema: ItemSchema
            An item schema of the source root that is one of
            `migrated_item_schemas`.

        Returns
        -------
        ItemSchema
            The item schema of the target root, of the same kind.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_attribute_schema(
        self, schema: AttributeSchema
    ) -> AttributeSchema | None:
        """Give the attribute schema of the target root that a source attribute
        schema migrates to.

        Parameters
        ----------
        schema: AttributeSchema
            An attribute schema of the source root, at any depth.

        Returns
        -------
        AttributeSchema | None
            The attribute schema of the target root, or None where it has none.
        """
        raise NotImplementedError()
