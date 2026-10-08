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

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Generic, TypeVar
from uuid import UUID

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeDeclarations,
    AttributeMigrator,
    AttributePair,
    NestedAttributeMigrator,
    UndeclaredAttributesError,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    DatasetSchema,
    Item,
    ItemSchema,
    MigratedObject,
    Project,
    ProjectSchema,
    UnresolvedAttribute,
)

ObjectSchema = ProjectSchema | DatasetSchema | ItemSchema
"""The schema of what is migrated: a project, a dataset, or an item."""

T = TypeVar("T", bound=Project | Dataset | Item)
DeclarationType = TypeVar("DeclarationType")


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
        migrated: Sequence[tuple[AttributeSchema, AttributeMigrator]] = (),
        renamed: Sequence[tuple[AttributeSchema, AttributeSchema]] = (),
        dropped: Iterable[AttributeSchema] = (),
    ):
        """Create a migrator between two schemas of the same kind.

        Parameters
        ----------
        source: ObjectSchema
            The project, dataset, or item schema of the source root.
        target: ObjectSchema
            The schema of the target root it becomes.
        migrated: Sequence[tuple[AttributeSchema, AttributeMigrator]] = ()
            Source attribute schemas whose values changed, with the migrator of
            their values.
        renamed: Sequence[tuple[AttributeSchema, AttributeSchema]] = ()
            Source attribute schemas, with the target attribute schema of another
            tag in the same object that each becomes.
        dropped: Iterable[AttributeSchema] = ()
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
        migrated_by_uid = self._index("migrated", migrated, lambda pair: pair[0])
        renamed_by_uid = self._index("renamed", renamed, lambda pair: pair[0])
        dropped_by_uid = self._index("dropped", dropped, lambda schema: schema)
        self._refuse_foreign(
            [
                ("migrated", [schema for schema, _ in migrated_by_uid.values()]),
                ("renamed", [schema for schema, _ in renamed_by_uid.values()]),
                ("dropped", list(dropped_by_uid.values())),
            ],
            [("renamed to", [schema for _, schema in renamed_by_uid.values()])],
        )
        declarations = AttributeDeclarations(
            {uid: migrator for uid, (_, migrator) in migrated_by_uid.items()},
            {uid: renamed_to for uid, (_, renamed_to) in renamed_by_uid.items()},
            dropped_by_uid.keys(),
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
        return self._source

    @property
    def target(self) -> ObjectSchema:
        return self._target

    def migrate(self, obj: T) -> MigratedObject:
        """The project, dataset, or item on the target schema."""
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
        """The migrator of a source attribute schema, at any depth, and the
        target attribute schema it migrates to, or None where it is dropped,
        held by a migrated attribute, or not of the source schema."""
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
        """The pairs of the attributes of the object, with the paths of those
        nothing is declared about added to `undeclared`."""
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
        """The attributes of the object by their tags in the target, with those
        that lost values put in `unresolved` instead."""
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

    def _index(
        self,
        declaration: str,
        declared: Iterable[DeclarationType],
        schema_of: Callable[[DeclarationType], AttributeSchema],
    ) -> dict[UUID, DeclarationType]:
        """The declared, by the uid of the attribute schema each is of, refusing
        an attribute schema declared twice."""
        indexed: dict[UUID, DeclarationType] = {}
        twice: list[str] = []
        for entry in declared:
            schema = schema_of(entry)
            if schema.uid in indexed:
                twice.append(f"{schema.tag} ({schema.uid})")
            indexed[schema.uid] = entry
        if twice:
            raise ValueError(
                f"The migrator of {self._source.name} declares "
                f"{', '.join(twice)} as {declaration} more than once."
            )
        return indexed

    def _refuse_foreign(
        self,
        of_source: Sequence[tuple[str, Sequence[AttributeSchema]]],
        of_target: Sequence[tuple[str, Sequence[AttributeSchema]]],
    ) -> None:
        """Refuse declarations, by name, of attribute schemas that are not of the
        source or target schema they are declared for."""
        sources = self._attribute_schemas(self._source)
        targets = self._attribute_schemas(self._target)
        foreign = [
            f"{schema.tag} ({schema.uid}) as {declaration}"
            for declarations, of in ((of_source, sources), (of_target, targets))
            for declaration, schemas in declarations
            for schema in schemas
            if schema.uid not in of
        ]
        if foreign:
            raise ValueError(
                f"The migrator of {self._source.name} declares "
                f"{', '.join(foreign)}, which are not attribute schemas of the "
                f"source or target schema they are declared for."
            )

    @staticmethod
    def _attribute_schemas(schema: ObjectSchema) -> set[UUID]:
        """The uids of the attribute schemas of an object schema, at any
        depth."""
        uids: set[UUID] = set()
        pending: list[AttributeSchema] = [
            *schema.attributes.values(),
            *schema.private_attributes.values(),
        ]
        while pending:
            attribute = pending.pop()
            uids.add(attribute.uid)
            pending.extend(NestedAttributeMigrator.held(attribute).values())
        return uids
