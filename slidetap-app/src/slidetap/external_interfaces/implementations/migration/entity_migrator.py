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

"""Migrating a project, a dataset, or an item to its schema on another root."""

from collections.abc import Mapping
from typing import Generic, TypeVar

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeMigrator,
    MigratedAttribute,
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnyAttribute,
    AnyEntitySchema,
    AttributeSchema,
    Dataset,
    EntityMigrationResult,
    Item,
    Project,
    UnresolvedAttributeMigration,
)

T = TypeVar("T", bound=Project | Dataset | Item)


class EntityMigrator(Generic[T]):
    """Migrates a project, a dataset, or an item from its schema in the source
    root to its schema in the target root.

    By default every attribute is moved as it is to the target attribute of
    its tag. A migrator of a schema that changed overrides `migrate()` and
    writes out what becomes of each attribute, with the helpers here: move an
    attribute as it is, move all but some, and migrate one with an attribute
    migrator, leaving it unresolved where it lost values.
    """

    def __init__(self, source: AnyEntitySchema, target: AnyEntitySchema):
        """Create a migrator between two schemas of the same kind.

        Parameters
        ----------
        source: AnyEntitySchema
            The project, dataset, or item schema of the source root.
        target: AnyEntitySchema
            The schema of the target root it becomes.
        """
        self._source = source
        self._target = target
        self._unchanged = UnchangedAttributeMigrator()

    @property
    def source(self) -> AnyEntitySchema:
        """The schema of the source root."""
        return self._source

    @property
    def target(self) -> AnyEntitySchema:
        """The schema of the target root."""
        return self._target

    def migrate(self, entity: T) -> EntityMigrationResult | None:
        """Migrate a project, dataset, or item to the target schema, moving
        every attribute as it is to the target attribute of its tag.

        Parameters
        ----------
        entity: T
            The project, dataset, or item, on the source schema. Not changed.

        Returns
        -------
        EntityMigrationResult | None
            The target schema and the attributes on it by target tag, or None
            where the entity is the same on the target schema, which a
            migrator may return only where the schema did not change.

        Raises
        ------
        ValueError
            If an attribute is held at a tag the target schema does not have.
        """
        return EntityMigrationResult(
            schema_uid=self._target.uid,
            attributes=self._move_all_except(entity.attributes),
            private_attributes=self._move_all_except(
                entity.private_attributes, private=True
            ),
        )

    def _move(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        """Move an attribute as it is to a target attribute schema, with what
        it holds at any depth.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute. Not changed.
        target: AttributeSchema
            The target attribute schema, holding the same values.

        Returns
        -------
        AnyAttribute
            The attribute on the target attribute schema.
        """
        return self._unchanged.migrate(attribute, target).attribute

    def _move_all_except(
        self,
        attributes: Mapping[str, AnyAttribute],
        *tags: str,
        private: bool = False,
    ) -> dict[str, AnyAttribute | UnresolvedAttributeMigration]:
        """Move attributes as they are to the target attributes of their tags,
        leaving out some.

        Parameters
        ----------
        attributes: Mapping[str, AnyAttribute]
            The attributes of the entity, public or private, by tag.
        *tags: str
            The tags of the attributes to leave out.
        private: bool = False
            Whether the attributes are the private ones.

        Returns
        -------
        dict[str, AnyAttribute | UnresolvedAttributeMigration]
            The attributes moved, by tag.

        Raises
        ------
        ValueError
            If an attribute moved is held at a tag the target schema does not
            have.
        """
        targets = (
            self._target.private_attributes if private else self._target.attributes
        )
        moved: dict[str, AnyAttribute | UnresolvedAttributeMigration] = {}
        for tag, attribute in attributes.items():
            if tag in tags:
                continue
            target = targets.get(tag)
            if target is None:
                raise ValueError(
                    f"Attribute {attribute.uid} is held as {tag!r}, which is not an "
                    f"attribute of the target schema of {self._source.name}."
                )
            moved[tag] = self._move(attribute, target)
        return moved

    def _migrate(
        self,
        attribute: AnyAttribute,
        migrator: AttributeMigrator,
        target: AttributeSchema,
    ) -> AnyAttribute | UnresolvedAttributeMigration:
        """Migrate an attribute with an attribute migrator, unresolved where
        its value in effect lost values.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute. Not changed.
        migrator: AttributeMigrator
            The migrator of its attribute schema, the one the migration
            registers for it, so that mapping items migrate alike.
        target: AttributeSchema
            The target attribute schema.

        Returns
        -------
        AnyAttribute | UnresolvedAttributeMigration
            The migrated attribute, or it unresolved.
        """
        return self._unresolve_lost(attribute, migrator.migrate(attribute, target))

    @staticmethod
    def _unresolve_lost(
        original: AnyAttribute, migrated: MigratedAttribute
    ) -> AnyAttribute | UnresolvedAttributeMigration:
        """Leave a migrated attribute unresolved where its value in effect lost
        values, with what could be migrated proposed.

        Parameters
        ----------
        original: AnyAttribute
            The attribute before it was migrated.
        migrated: MigratedAttribute
            The attribute migrated, and what it lost.

        Returns
        -------
        AnyAttribute | UnresolvedAttributeMigration
            The migrated attribute where it lost nothing, else it unresolved.
        """
        if not migrated.lost:
            return migrated.attribute
        return UnresolvedAttributeMigration(
            original=original,
            proposed=migrated.attribute,
            problem=" ".join(migrated.lost),
        )
