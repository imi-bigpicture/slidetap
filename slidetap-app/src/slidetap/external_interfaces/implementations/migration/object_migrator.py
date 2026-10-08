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

from collections.abc import Iterable, Mapping, Sequence
from typing import Generic, TypeVar
from uuid import UUID

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeDeclarations,
    AttributeMigrator,
    AttributePair,
    ObjectSchema,
    UndeclaredAttributesError,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    Item,
    MigratedObject,
    Project,
    UnresolvedAttribute,
)

T = TypeVar("T", bound=Project | Dataset | Item)


class ObjectMigrator(Generic[T]):
    """Migrates a project, a dataset, or an item from its schema in the source
    root to its schema in the target root.

    Every attribute whose tag is in both schemas is moved to the target
    attribute of that tag, at any depth, with the attributes it holds. What
    else becomes of an attribute is declared by its source attribute schema, at
    any depth: migrated by an attribute migrator, such as an enum whose values
    changed, renamed to another attribute of the same object, or dropped. A
    target attribute that no source attribute becomes is left without a value.

    A migrator is refused when it is created if a declaration is not of the
    schemas, or if it says nothing about a source attribute it cannot move as
    it is: one whose tag is not in the target, or whose target is of another
    kind or, for an enum, holds other values.

    An attribute whose value in effect loses values to an attribute migrator,
    at any depth, is returned unresolved, under its target tag, with what could
    be migrated proposed.
    """

    def __init__(
        self,
        source: ObjectSchema,
        target: ObjectSchema,
        migrated_attributes: Sequence[tuple[AttributeSchema, AttributeMigrator]] = (),
        renamed_attributes: Sequence[tuple[AttributeSchema, AttributeSchema]] = (),
        dropped_attributes: Iterable[AttributeSchema] = (),
    ):
        """Create a migrator between two schemas of the same kind.

        Parameters
        ----------
        source: ObjectSchema
            The project, dataset, or item schema of the source root.
        target: ObjectSchema
            The schema of the target root it becomes.
        migrated_attributes: Sequence[tuple[AttributeSchema, AttributeMigrator]] = ()
            Source attribute schemas whose values changed, with the migrator of
            their values.
        renamed_attributes: Sequence[tuple[AttributeSchema, AttributeSchema]] = ()
            Source attribute schemas, with the target attribute schema of another
            tag in the same object that each becomes.
        dropped_attributes: Iterable[AttributeSchema] = ()
            Source attribute schemas that are left out.

        Raises
        ------
        ValueError
            If an attribute schema is declared twice in a declaration, a
            declared attribute schema is not of the schema it is declared for,
            or the migrator says nothing about a source attribute it cannot
            move as it is.
        """
        self._source = source
        self._target = target
        declarations = AttributeDeclarations(
            source, target, migrated_attributes, renamed_attributes, dropped_attributes
        )
        undeclared: list[str] = []
        self._attributes = self._pair(
            declarations, source.attributes, target.attributes, "", undeclared
        )
        self._private_attributes = self._pair(
            declarations,
            source.private_attributes,
            target.private_attributes,
            "!",
            undeclared,
        )
        if undeclared:
            raise ValueError(
                f"The migrator of {source.name} says nothing about "
                f"{', '.join(undeclared)}, which cannot be moved as it is to the "
                f"target schema."
            )

    @property
    def source(self) -> ObjectSchema:
        """The schema of the source root."""
        return self._source

    @property
    def target(self) -> ObjectSchema:
        """The schema of the target root."""
        return self._target

    def migrate(self, obj: T) -> MigratedObject:
        """Migrate a project, dataset, or item to the target schema.

        Parameters
        ----------
        obj: T
            The project, dataset, or item, on the source schema. Not changed.

        Returns
        -------
        MigratedObject
            The target schema, the attributes on it by target tag, and the
            attributes whose value in effect lost values as unresolved.

        Raises
        ------
        ValueError
            If an attribute is held at a tag that is not of the source schema.
        """
        unresolved: dict[str, UnresolvedAttribute] = {}
        attributes = self._migrate_attributes(
            obj.attributes, self._attributes, unresolved
        )
        private_attributes = self._migrate_attributes(
            obj.private_attributes, self._private_attributes, unresolved
        )
        return MigratedObject(
            schema_uid=self._target.uid,
            attributes=attributes,
            private_attributes=private_attributes,
            unresolved=unresolved,
        )

    def attribute_migrator_of(
        self, schema_uid: UUID
    ) -> tuple[AttributeMigrator, AttributeSchema] | None:
        """Find the migrator of a source attribute schema, at any depth.

        Parameters
        ----------
        schema_uid: UUID
            The uid of the source attribute schema.

        Returns
        -------
        tuple[AttributeMigrator, AttributeSchema] | None
            The migrator and the target attribute schema it migrates to, or
            None where it is dropped, held by a migrated attribute, or not of
            the source schema.
        """
        for pair in (*self._attributes.values(), *self._private_attributes.values()):
            if pair is None:
                continue
            found = pair.attribute_migrator_of(schema_uid)
            if found is not None:
                return found
        return None

    @staticmethod
    def _pair(
        declarations: AttributeDeclarations,
        sources: Mapping[str, AttributeSchema],
        targets: Mapping[str, AttributeSchema],
        path_prefix: str,
        undeclared: list[str],
    ) -> dict[str, AttributePair | None]:
        """Pair the attributes of the object, adding the paths of those nothing
        is declared about to `undeclared`."""
        try:
            return declarations.pair(sources, targets, path_prefix)
        except UndeclaredAttributesError as error:
            undeclared.extend(error.paths)
            return {}

    def _migrate_attributes(
        self,
        attributes: Mapping[str, AnyAttribute],
        pairs: Mapping[str, AttributePair | None],
        unresolved: dict[str, UnresolvedAttribute],
    ) -> dict[str, AnyAttribute]:
        """Migrate the attributes of the object to their tags in the target,
        putting those that lost values in `unresolved` instead.

        Raises
        ------
        ValueError
            If an attribute is held at a tag that is not of the source schema.
        """
        migrated: dict[str, AnyAttribute] = {}
        for source_tag, attribute in attributes.items():
            if source_tag not in pairs:
                raise ValueError(
                    f"Attribute {attribute.uid} is held as {source_tag!r}, which is "
                    f"not an attribute of the source schema of {self._source.name}."
                )
            pair = pairs[source_tag]
            if pair is None:
                continue
            result = pair.migrate(attribute)
            if result.lost:
                unresolved[pair.target_key] = UnresolvedAttribute(
                    original=attribute,
                    proposed=result.attribute,
                    reason=" ".join(dict.fromkeys(result.lost)),
                )
            else:
                migrated[pair.target_key] = result.attribute
        return migrated
