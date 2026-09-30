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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from slidetap.model import AnyAttribute, Dataset, Item, Project


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


class SchemaMigration(metaclass=ABCMeta):
    """Moves the projects on one root schema to another root of its family, one
    project, dataset, or item at a time.

    Every object of a project is given to the migration, which returns what it
    is on the target root. `AttributeMigrator` moves an attribute whose values
    are unchanged to the attribute schema of another root. Changes across
    objects are not supported.
    """

    @property
    @abstractmethod
    def source_root_uid(self) -> UUID:
        """The uid of the root schema the projects are moved from."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def target_root_uid(self) -> UUID:
        """The uid of the root schema the projects are moved to."""
        raise NotImplementedError()

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


class SchemaMigrationInterface(metaclass=ABCMeta):
    """Provides the migrations of the projects on the plugin's root schemas.

    Optional: an application that provides one root has nothing to migrate.
    """

    @property
    @abstractmethod
    def migrations(self) -> Sequence[SchemaMigration]:
        """The migrations, at most one from each root.

        Checked when loaded: both roots must be provided and of the same
        family, and a root can only be migrated from by one migration.
        """
        raise NotImplementedError()
