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
from uuid import UUID

from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    Item,
    MetadataSearchItem,
    MigratedObject,
    Project,
)


class SchemaMigration(metaclass=ABCMeta):
    """Migrates projects, datasets, items, and search items from a previous root
    schema to the root of new projects, one object at a time.

    Each method returns what the object is on the target root. What a migration
    cannot migrate by itself it returns as unresolved, for a curator to decide;
    it is then run again to complete the migration, and must return the same.
    Changes across objects are not supported.

    `DeclarativeSchemaMigration` implements it from declared object migrators.
    """

    @abstractmethod
    def migrate_project(self, project: Project) -> MigratedObject:
        """Migrate a project from its schema on the source root to the target root.

        Parameters
        ----------
        project: Project
            The project, on the project schema of the source root.

        Returns
        -------
        MigratedObject
            The project schema of the target root, the project's attributes on
            it, and the attributes that need a curator's decision as unresolved.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_dataset(self, dataset: Dataset) -> MigratedObject:
        """Migrate a dataset from its schema on the source root to the target root.

        Parameters
        ----------
        dataset: Dataset
            The dataset, on the dataset schema of the source root.

        Returns
        -------
        MigratedObject
            The dataset schema of the target root, the dataset's attributes on
            it, and the attributes that need a curator's decision as unresolved.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_item(self, item: Item) -> MigratedObject:
        """Migrate an item from its schema on the source root to the target root.

        Parameters
        ----------
        item: Item
            The item: a sample, image, annotation, or observation, on an item
            schema of the source root.

        Returns
        -------
        MigratedObject
            The item schema of the target root, of the same kind, the item's
            attributes on it, and the attributes that need a curator's decision
            as unresolved.
        """
        raise NotImplementedError()

    @abstractmethod
    def migrate_search_item(self, search_item: MetadataSearchItem) -> UUID:
        """Give the item schema of the target root for a search item on an item
        schema of the source root.

        A search item records what a search of a batch found, or failed to
        find, by identifier and item schema, also where no item was imported.

        Parameters
        ----------
        search_item: MetadataSearchItem
            The search item, on an item schema of the source root.

        Returns
        -------
        UUID
            The uid of the item schema of the target root, of the same kind as
            the one the search item is on.
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
