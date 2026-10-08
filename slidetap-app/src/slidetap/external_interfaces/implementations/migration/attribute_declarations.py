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


"""Pairing the attribute schemas of a source entity schema with those of the
target entity schema they become, by what is declared about them."""

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeMigrator,
    MigratedAttribute,
    NestedAttributeMigrator,
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnyAttribute,
    AnyEntitySchema,
    AttributeSchema,
    EnumAttributeSchema,
)

DeclarationType = TypeVar("DeclarationType")


@dataclass(frozen=True)
class AttributePair:
    """A source attribute schema, the target attribute schema it becomes, and
    the migrator between them."""

    target_key: str
    """The key of the target among the attributes held with it."""

    source: AttributeSchema
    """The attribute schema of the source root."""

    target: AttributeSchema
    """The attribute schema of the target root it becomes."""

    migrator: AttributeMigrator
    """The migrator from the source to the target."""

    def migrate(self, attribute: AnyAttribute) -> MigratedAttribute:
        """Migrate an attribute of the source to the target.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute, on the source attribute schema. Not changed.

        Returns
        -------
        MigratedAttribute
            The attribute on the target attribute schema, and what it lost.
        """
        return self.migrator.migrate(attribute, self.target)

    def attribute_migrators(
        self,
    ) -> Iterator[tuple[UUID, AttributeMigrator, AttributeSchema]]:
        """Iterate the migrators of the pair and of what it holds, at any depth.

        Returns
        -------
        Iterator[tuple[UUID, AttributeMigrator, AttributeSchema]]
            The uid of each source attribute schema, its migrator, and the
            target attribute schema it migrates to, starting with the pair's.
        """
        yield self.source.uid, self.migrator, self.target
        if isinstance(self.migrator, NestedAttributeMigrator):
            yield from self.migrator.attribute_migrators()


class UndeclaredAttributesError(ValueError):
    """Source attributes that nothing is declared about but that cannot be
    moved as they are to the target schema."""

    def __init__(self, paths: Sequence[str]):
        """Create the error.

        Parameters
        ----------
        paths: Sequence[str]
            The paths of the source attribute schemas, by key from where they
            were paired.
        """
        self.paths = tuple(paths)
        super().__init__(
            f"Nothing is declared about {', '.join(self.paths)}, which cannot be "
            f"moved as it is to the target schema."
        )


class AttributeDeclarations:
    """What is declared about the attribute schemas of a source entity schema,
    by their uid: the migrator of those whose values changed, the target
    attribute schema of those renamed, and those dropped.

    Pairs source attribute schemas with target attribute schemas, building the
    migrator of each pair: the declared one, a `NestedAttributeMigrator` for an
    object, list, or union, or an `UnchangedAttributeMigrator`.
    """

    def __init__(
        self,
        source: AnyEntitySchema,
        target: AnyEntitySchema,
        migrated: Iterable[tuple[AttributeSchema, AttributeMigrator]] = (),
        renamed: Iterable[tuple[AttributeSchema, AttributeSchema]] = (),
        dropped: Iterable[AttributeSchema] = (),
    ):
        """Create the declarations about the attribute schemas of a source
        entity schema.

        Parameters
        ----------
        source: AnyEntitySchema
            The project, dataset, or item schema of the source root.
        target: AnyEntitySchema
            The schema of the target root it becomes.
        migrated: Iterable[tuple[AttributeSchema, AttributeMigrator]] = ()
            Source attribute schemas whose values changed, with the migrator of
            their values.
        renamed: Iterable[tuple[AttributeSchema, AttributeSchema]] = ()
            Source attribute schemas, with the target attribute schema of another
            tag in the same object that each becomes.
        dropped: Iterable[AttributeSchema] = ()
            Source attribute schemas that are left out.

        Raises
        ------
        ValueError
            If an attribute schema is declared twice in a declaration, or a
            declared attribute schema is not of the schema it is declared for.
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
        self._migrated = {
            uid: migrator for uid, (_, migrator) in migrated_by_uid.items()
        }
        self._renamed = {
            uid: renamed_to for uid, (_, renamed_to) in renamed_by_uid.items()
        }
        self._dropped = dropped_by_uid.keys()
        self._unchanged = UnchangedAttributeMigrator()

    def pair(
        self,
        sources: Mapping[str, AttributeSchema],
        targets: Mapping[str, AttributeSchema],
        path_prefix: str = "",
    ) -> dict[str, AttributePair | None]:
        """Pair source attribute schemas with the target attribute schemas they
        become.

        Parameters
        ----------
        sources: Mapping[str, AttributeSchema]
            The source attribute schemas, by key.
        targets: Mapping[str, AttributeSchema]
            The target attribute schemas held with them, by key.
        path_prefix: str = ""
            The prefix of the paths in an error.

        Returns
        -------
        dict[str, AttributePair | None]
            The pair of every source attribute schema, by its key, None for one
            that is dropped.

        Raises
        ------
        UndeclaredAttributesError
            With the paths, prefixed, of the source attribute schemas that
            cannot be moved as they are and have nothing declared about them,
            at any depth.
        """
        pairs: dict[str, AttributePair | None] = {}
        undeclared: list[str] = []
        for key, source in sources.items():
            path = path_prefix + key
            if source.uid in self._dropped:
                pairs[key] = None
                continue
            target_key = self._target_key(key, source, targets)
            if target_key is None:
                undeclared.append(path)
                continue
            target = targets[target_key]
            try:
                migrator = self._migrator(source, target)
            except UndeclaredAttributesError as error:
                undeclared.extend(path + nested for nested in error.paths)
                continue
            pairs[key] = AttributePair(target_key, source, target, migrator)
        if undeclared:
            raise UndeclaredAttributesError(undeclared)
        return pairs

    def _migrator(
        self, source: AttributeSchema, target: AttributeSchema
    ) -> AttributeMigrator:
        """Build the migrator from a source to a target attribute schema: the
        declared one, a nested one, or the unchanged one.

        Raises
        ------
        UndeclaredAttributesError
            If the source cannot be moved as it is, or holds one that cannot,
            and nothing is declared about it.
        """
        declared = self._migrated.get(source.uid)
        if declared is not None:
            return declared
        if self._differ(source, target):
            raise UndeclaredAttributesError([""])
        if NestedAttributeMigrator.held(source):
            return NestedAttributeMigrator(source, target, self)
        return self._unchanged

    def _target_key(
        self, key: str, source: AttributeSchema, targets: Mapping[str, AttributeSchema]
    ) -> str | None:
        """Find the key of the target attribute a source attribute becomes,
        None if it has none among the targets."""
        renamed_to = self._renamed.get(source.uid)
        if renamed_to is None:
            return key if key in targets else None
        return next(
            (
                target_key
                for target_key, target in targets.items()
                if target.uid == renamed_to.uid
            ),
            None,
        )

    @staticmethod
    def _differ(source: AttributeSchema, target: AttributeSchema) -> bool:
        """Check if a source attribute cannot be moved as it is to the target:
        one of another kind, or an enum of other values."""
        if type(source) is not type(target):
            return True
        return (
            isinstance(source, EnumAttributeSchema)
            and isinstance(target, EnumAttributeSchema)
            and set(source.allowed_values) != set(target.allowed_values)
        )

    def _index(
        self,
        declaration: str,
        declared: Iterable[DeclarationType],
        schema_of: Callable[[DeclarationType], AttributeSchema],
    ) -> dict[UUID, DeclarationType]:
        """Index declarations by the uid of the attribute schema each is of.

        Raises
        ------
        ValueError
            If an attribute schema is declared twice.
        """
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
        source or target schema they are declared for.

        Raises
        ------
        ValueError
            If a declared attribute schema is not of the schema it is declared
            for.
        """
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
    def _attribute_schemas(schema: AnyEntitySchema) -> set[UUID]:
        """Collect the uids of the attribute schemas of an entity schema, at
        any depth."""
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
