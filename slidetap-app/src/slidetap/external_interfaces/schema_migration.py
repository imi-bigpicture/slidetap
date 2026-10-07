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
from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import UUID

from slidetap.model import AnyAttribute, Dataset, Item, MetadataSearchItem, Project


@dataclass(frozen=True)
class Unresolved:
    """An attribute a migration could not convert by itself, for the curator
    to decide."""

    original: AnyAttribute | None
    """The attribute of the source object, or None where it had none."""

    proposed: AnyAttribute | None
    """What could be converted, on the attribute schema of the target tag, for
    the curator to start from, or None."""

    reason: str
    """Why the attribute was not converted."""


@dataclass(frozen=True)
class MigratedObject:
    """What a migration may change of a project, dataset, or item: the schema
    it is on, and its attributes.

    Everything else, such as the uid, the relations, the images, the review
    status, and the pseudonym, is kept by core as it is.
    """

    schema_uid: UUID
    """The project, dataset, or item schema of the target root, of the same
    kind as the one it was on."""

    attributes: Mapping[str, AnyAttribute] = field(default_factory=dict)
    """The attributes by tag, each on the attribute schema of that tag in the
    target schema. An attribute left out is dropped."""

    private_attributes: Mapping[str, AnyAttribute] = field(default_factory=dict)
    """The private attributes, as `attributes`."""

    unresolved: Mapping[str, Unresolved] = field(default_factory=dict)
    """What the curator decides, by tag of the target schema, a public or else
    a private attribute, which is in neither `attributes` nor
    `private_attributes`. The decided value is put at the tag, or nothing."""


class SchemaMigration(metaclass=ABCMeta):
    """Moves the projects on a previous root schema to the root of new
    projects, one project, dataset, or item at a time.

    Every object of a project, and every search item of its batches, is given
    to the migration, which returns what it is on the target root. What it
    cannot convert by itself it returns as unresolved, for the curator to
    decide before the migration is completed. The migration is run again to
    complete it, and must return the same.

    `ConvertingSchemaMigration` implements a migration from declared object
    converters, and `AttributeMigrator` moves an attribute whose values are
    unchanged to the attribute schema of another root. Changes across objects
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
