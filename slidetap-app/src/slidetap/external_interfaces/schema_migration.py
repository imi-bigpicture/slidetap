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
    Dataset,
    Item,
    MetadataSearchItem,
    MigratedObject,
    Project,
)


class SchemaMigration(metaclass=ABCMeta):
    """Moves the projects on a previous root schema to the root of new
    projects, one project, dataset, or item at a time.

    Every object of a project, and every search item of its batches, is given
    to the migration, which returns what it is on the target root. What it
    cannot convert by itself it returns as unresolved, for the curator to
    decide before the migration is completed. The migration is run again to
    complete it, and must return the same.

    `DeclarativeSchemaMigration` implements a migration from declared object
    migrators, and `UnchangedAttributeMigrator` moves an attribute whose values
    are unchanged to the attribute schema of another root. Changes across objects
    are not supported.
    """

    @abstractmethod
    def migrate_project(self, project: Project) -> MigratedObject:
        """The project on the target root."""
        raise NotImplementedError()

    @abstractmethod
    def migrate_dataset(self, dataset: Dataset) -> MigratedObject:
        """The dataset on the target root."""
        raise NotImplementedError()

    @abstractmethod
    def migrate_item(self, item: Item) -> MigratedObject:
        """The item on the target root."""
        raise NotImplementedError()

    @abstractmethod
    def migrate_search_item(self, search_item: MetadataSearchItem) -> UUID:
        """The uid of the item schema of the target root a search item is
        moved to, of the same kind as the one it is on.

        A search item records what a search of a batch found or failed to,
        by identifier and item schema, also where no item was imported.
        """
        raise NotImplementedError()

    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        """The attribute on the attribute schema of the target root it is moved
        to, or None where it has none.

        Used for mappers, not for projects: a mapper of an attribute given
        another schema is moved to that schema, which is found by migrating an
        empty attribute, and each of its mapping items is converted by this.
        A mapping item converted to None is removed. The default, None, leaves
        the mappers as they are.
        """
        return None
