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

"""Migrating an attribute to the attribute schema of another root."""

from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar, cast
from uuid import UUID

from slidetap.model import (
    AnyAttribute,
    AnyAttributeSchema,
    Attribute,
    AttributeSchema,
    AttributeValueType,
    DatasetSchema,
    EnumAttribute,
    EnumAttributeSchema,
    ItemSchema,
    ListAttributeSchema,
    ObjectAttributeSchema,
    ProjectSchema,
    RejectedValues,
    UnionAttributeSchema,
)

ObjectSchema = ProjectSchema | DatasetSchema | ItemSchema
"""The schema of what is migrated: a project, a dataset, or an item."""

DeclarationType = TypeVar("DeclarationType")


@dataclass(frozen=True)
class MigratedAttribute:
    """An attribute migrated to the target schema."""

    attribute: AnyAttribute
    """The migrated attribute, with the same uid."""

    lost: tuple[str, ...] = ()
    """Why the value in effect lost values that have no counterpart on the
    target schema, empty where it lost none."""


class AttributeMigrator(metaclass=ABCMeta):
    """Migrates an attribute to the attribute schema of the target root.

    Two migrators are equal where they migrate alike: the migrators here
    compare their type and what they are created with, and any other is equal
    to itself only.
    """

    @abstractmethod
    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
        """Migrate an attribute to the target schema, with its values.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to migrate. Not changed.
        target: AttributeSchema
            The attribute schema of the target root to migrate it to.

        Returns
        -------
        MigratedAttribute
            The migrated attribute, without a value where the value it had has
            no counterpart on the target schema, and why.
        """
        raise NotImplementedError()


class UnchangedAttributeMigrator(AttributeMigrator):
    """Copies an attribute to a target attribute schema, for an attribute whose
    values are the same on the target root.

    What an attribute holds is kept: its three values, what it was left to map,
    what was refused of it, how it is shown, and its mapping item. What refers
    to a schema is moved: the schema uid of the attribute, and of every
    attribute nested in its values. A nested attribute is moved to the
    attribute of the same tag in an object, to the attribute of a list, and to
    the member of the same value type in a union.
    """

    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
        """Copy an attribute to the target schema.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to migrate. Not changed.
        target: AttributeSchema
            The attribute schema of the target root to copy it to.

        Returns
        -------
        MigratedAttribute
            The attribute on the target schema, with what it nests moved to the
            nested schemas of the target, and nothing lost.

        Raises
        ------
        ValueError
            If the target, or a schema it nests, is of another value type, as
            the values of the attribute could not be held by it.
        """
        return MigratedAttribute(self._move(attribute, target))

    def __eq__(self, other: object) -> bool:
        """Check if another migrator is an unchanged migrator too, which holds
        nothing of its own."""
        return type(other) is type(self)

    def __hash__(self) -> int:
        """Hash the migrator by its type."""
        return hash(type(self))

    def _move(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        """Move an attribute and what it nests to a target schema.

        Raises
        ------
        ValueError
            If the target is of another value type.
        """
        if attribute.attribute_value_type != self._value_type(target):
            raise ValueError(
                f"Cannot move attribute {attribute.uid} of value type "
                f"{attribute.attribute_value_type.name} to schema {target.uid} of "
                f"value type {self._value_type(target).name}."
            )
        update: dict[str, Any] = {
            "schema_uid": target.uid,
            "original_value": self._move_value(attribute.original_value, target),
            "updated_value": self._move_value(attribute.updated_value, target),
            "mapped_value": self._move_value(attribute.mapped_value, target),
        }
        return attribute.model_copy(update=update, deep=True)

    def _move_value(self, value: Any, target: AttributeSchema) -> Any:
        """Move what a value of an attribute nests to the nested schemas of the
        target."""
        if value is None:
            return None
        if isinstance(target, ObjectAttributeSchema) and isinstance(value, Mapping):
            return {
                tag: self._move(nested, self._nested_of_object(target, tag))
                for tag, nested in value.items()
            }
        if isinstance(target, ListAttributeSchema) and isinstance(value, Sequence):
            return [self._move(nested, target.attribute) for nested in value]
        if isinstance(target, UnionAttributeSchema):
            return self._move(value, self._member_of_union(target, value))
        return value

    @staticmethod
    def _nested_of_object(target: ObjectAttributeSchema, tag: str) -> AttributeSchema:
        """Return the attribute schema of a tag in an object attribute schema.

        Raises
        ------
        ValueError
            If the object attribute schema has no attribute of the tag.
        """
        nested = target.attributes.get(tag)
        if nested is None:
            raise ValueError(
                f"Object attribute schema {target.uid} has no attribute {tag!r} to "
                f"move a nested attribute to."
            )
        return nested

    @staticmethod
    def _member_of_union(
        target: UnionAttributeSchema, value: AnyAttribute
    ) -> AttributeSchema:
        """Return the member a union's value is moved to: the one of its own
        schema where the target has it, else the first of its value type.

        Raises
        ------
        ValueError
            If the union has no member of the value type of the value.
        """
        members = [
            member
            for member in target.attributes
            if UnchangedAttributeMigrator._value_type(member)
            == value.attribute_value_type
        ]
        if not members:
            raise ValueError(
                f"Union attribute schema {target.uid} has no member of value type "
                f"{value.attribute_value_type.name}."
            )
        for member in members:
            if member.uid == value.schema_uid:
                return member
        return members[0]

    @staticmethod
    def _value_type(schema: AttributeSchema) -> AttributeValueType:
        """Return the value type of a schema, which every concrete schema
        declares."""
        return cast(AnyAttributeSchema, schema).attribute_value_type

    @classmethod
    def without_mapping_items(
        cls, attribute: AnyAttribute, removed: Callable[[UUID], bool]
    ) -> AnyAttribute:
        """Clear the references of an attribute to the mapping items that are
        removed, its own and those of the attributes nested in its values.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute. Not changed.
        removed: Callable[[UUID], bool]
            Whether a mapping item is removed.

        Returns
        -------
        AnyAttribute
            A copy, with what was mapped kept and the mapping it was mapped by
            cleared where that is removed.
        """
        update: dict[str, Any] = {
            key: cls._value_without_mapping_items(getattr(attribute, key), removed)
            for key in ("original_value", "updated_value", "mapped_value")
        }
        if attribute.mapping_item_uid is not None and removed(
            attribute.mapping_item_uid
        ):
            update["mapping_item_uid"] = None
        return attribute.model_copy(update=update)

    @classmethod
    def _value_without_mapping_items(
        cls, value: Any, removed: Callable[[UUID], bool]
    ) -> Any:
        """Clear the references to removed mapping items of the attributes a
        value nests."""
        if isinstance(value, Attribute):
            return cls.without_mapping_items(cast(AnyAttribute, value), removed)
        if isinstance(value, Mapping):
            return {
                key: cls._value_without_mapping_items(nested, removed)
                for key, nested in value.items()
            }
        if isinstance(value, list | tuple):
            return [
                cls._value_without_mapping_items(nested, removed) for nested in value
            ]
        return value


class EnumAttributeMigrator(AttributeMigrator):
    """Migrates the values of an enum attribute from one enum to another, value
    by value, through the member of the source enum to the member of the same
    name in the target enum.

    Only what does not follow the names is listed as an exception: a source
    member that became another target member, or that has no target member.
    A value without a target member is cleared.

    The original, updated, and mapped values are migrated each on their own.
    What the attribute was left to map, what was refused of it, how it is shown,
    and its mapping item are kept. Where the value in effect has no target, the
    attribute is left without one, which is reported as lost: the values below
    it are refused, so that one of them does not take its place.
    """

    def __init__(
        self,
        source_type: type[Enum],
        target_type: type[Enum],
        exceptions: Mapping[Enum, Enum | None] | None = None,
    ):
        """Create a migrator between the values of two enums.

        Parameters
        ----------
        source_type: type[Enum]
            The enum of the source root.
        target_type: type[Enum]
            The enum of the target root.
        exceptions: Mapping[Enum, Enum | None] | None = None
            Source members that do not become the target member of the same
            name, to the target member they become, or None where they have
            none.
        """
        self._source_type = source_type
        self._target_type = target_type
        self._exceptions = dict(exceptions or {})

    @property
    def source_type(self) -> type[Enum]:
        """The enum of the source root."""
        return self._source_type

    @property
    def target_type(self) -> type[Enum]:
        """The enum of the target root."""
        return self._target_type

    @property
    def exceptions(self) -> Mapping[Enum, Enum | None]:
        """The source members that do not become the target member of the
        same name, to the target member they become or None."""
        return self._exceptions

    @property
    def values(self) -> dict[str, str | None]:
        """The target value of every source value, None for one without."""
        return {
            member.value: self.migrate_value(member.value)
            for member in self._source_type
        }

    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
        """Migrate an enum attribute to the target schema, value by value.

        Parameters
        ----------
        attribute: AnyAttribute
            The enum attribute to migrate. Not changed.
        target: AttributeSchema
            The enum attribute schema of the target root to migrate it to.

        Returns
        -------
        MigratedAttribute
            The attribute with its values migrated, and, where the value in
            effect has no target value, the values below it refused and why it
            was lost.

        Raises
        ------
        TypeError
            If the attribute is not an enum attribute.
        """
        if not isinstance(attribute, EnumAttribute):
            raise TypeError(f"Attribute {attribute.uid} is not an enum attribute.")
        rejected = attribute.rejected
        lost: tuple[str, ...] = ()
        if attribute.value is not None and self.migrate_value(attribute.value) is None:
            rejected |= self._below(attribute)
            lost = (
                f"'{attribute.value}' is no longer an option of {target.display_name}.",
            )
        migrated = attribute.model_copy(
            update={
                "schema_uid": target.uid,
                "original_value": self.migrate_value(attribute.original_value),
                "updated_value": self.migrate_value(attribute.updated_value),
                "mapped_value": self.migrate_value(attribute.mapped_value),
                "rejected": rejected,
            },
            deep=True,
        )
        return MigratedAttribute(migrated, lost)

    def __eq__(self, other: object) -> bool:
        """Check if another migrator is an enum migrator between the same enums,
        with the same exceptions."""
        return (
            isinstance(other, EnumAttributeMigrator)
            and type(other) is type(self)
            and other._source_type is self._source_type
            and other._target_type is self._target_type
            and other._exceptions == self._exceptions
        )

    def __hash__(self) -> int:
        """Hash the migrator by its type and enums."""
        return hash((type(self), self._source_type, self._target_type))

    def migrate_value(self, value: str | None) -> str | None:
        """Migrate a value of the source enum to the target enum.

        Parameters
        ----------
        value: str | None
            The value of a member of the source enum, or None.

        Returns
        -------
        str | None
            The value of the target member it becomes, or None where it has
            none, is None, or is not a value of the source enum.
        """
        if value is None:
            return None
        try:
            member = self._source_type(value)
        except ValueError:
            # Not a value of the source enum either, so nothing to migrate.
            return None
        if member in self._exceptions:
            target_member = self._exceptions[member]
            return None if target_member is None else target_member.value
        if member.name not in self._target_type.__members__:
            return None
        return self._target_type[member.name].value

    @staticmethod
    def _below(attribute: EnumAttribute) -> RejectedValues:
        """Return the values below the one in effect, which would be in effect
        if it were cleared."""
        if attribute.updated_value is not None:
            return RejectedValues.MAPPABLE | RejectedValues.ORIGINAL
        if attribute.mapped_value is not None and (
            RejectedValues.MAPPABLE not in attribute.rejected
        ):
            return RejectedValues.ORIGINAL
        return RejectedValues.NONE


class FixedValueAttributeMigrator(AttributeMigrator):
    """Sets an attribute to a value the target root requires, whatever it held.

    The value is set as what the attribute was imported with, and what was
    edited or mapped is cleared. Nothing of it is left refused, so the value is
    the attribute's even where a curator had refused what it held.
    """

    def __init__(self, value: str):
        """Create a migrator that sets a value.

        Parameters
        ----------
        value: str
            The value the target root requires.
        """
        self._value = value

    @property
    def value(self) -> str:
        """The value the target root requires."""
        return self._value

    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
        """Set an attribute on the target schema to the value.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to migrate. Not changed.
        target: AttributeSchema
            The attribute schema of the target root to migrate it to.

        Returns
        -------
        MigratedAttribute
            The attribute with the value as its original value, nothing else
            held or refused, and nothing lost.
        """
        migrated = attribute.model_copy(
            update={
                "schema_uid": target.uid,
                "original_value": self._value,
                "updated_value": None,
                "mapped_value": None,
                "mappable_value": None,
                "mapping_item_uid": None,
                "rejected": RejectedValues.NONE,
            },
            deep=True,
        )
        return MigratedAttribute(migrated)

    def __eq__(self, other: object) -> bool:
        """Check if another migrator sets the same value."""
        return (
            isinstance(other, FixedValueAttributeMigrator)
            and type(other) is type(self)
            and other._value == self._value
        )

    def __hash__(self) -> int:
        """Hash the migrator by its type and value."""
        return hash((type(self), self._value))


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
    """What is declared about the attribute schemas of a source object schema,
    by their uid: the migrator of those whose values changed, the target
    attribute schema of those renamed, and those dropped.

    Pairs source attribute schemas with target attribute schemas, building the
    migrator of each pair: the declared one, a `NestedAttributeMigrator` for an
    object, list, or union, or an `UnchangedAttributeMigrator`.
    """

    def __init__(
        self,
        source: ObjectSchema,
        target: ObjectSchema,
        migrated: Iterable[tuple[AttributeSchema, AttributeMigrator]] = (),
        renamed: Iterable[tuple[AttributeSchema, AttributeSchema]] = (),
        dropped: Iterable[AttributeSchema] = (),
    ):
        """Create the declarations about the attribute schemas of a source
        object schema.

        Parameters
        ----------
        source: ObjectSchema
            The project, dataset, or item schema of the source root.
        target: ObjectSchema
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
    def _attribute_schemas(schema: ObjectSchema) -> set[UUID]:
        """Collect the uids of the attribute schemas of an object schema, at
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


class NestedAttributeMigrator(AttributeMigrator):
    """Migrates an object, list, or union attribute by migrating the attributes
    it holds, each with the migrator of its attribute schema.

    The original, updated, and mapped values are migrated each on their own.
    Only what the value in effect lost is reported as lost. A member of a union
    is migrated to the member of the same position in the target union.
    """

    def __init__(
        self,
        source: AttributeSchema,
        target: AttributeSchema,
        declarations: AttributeDeclarations,
    ):
        """Create the migrator of an object, list, or union attribute schema.

        Parameters
        ----------
        source: AttributeSchema
            The attribute schema of the source root.
        target: AttributeSchema
            The attribute schema of the target root, of the same kind.
        declarations: AttributeDeclarations
            What is declared about the attribute schemas it holds.

        Raises
        ------
        UndeclaredAttributesError
            If an attribute schema it holds, at any depth, cannot be moved as
            it is and nothing is declared about it.
        """
        self._source = source
        self._target = target
        self._pairs = declarations.pair(
            self.held(source),
            self.held(target),
            "/" if isinstance(source, ObjectAttributeSchema) else "",
        )

    @property
    def source(self) -> AttributeSchema:
        """The attribute schema of the source root."""
        return self._source

    @property
    def target(self) -> AttributeSchema:
        """The attribute schema of the target root."""
        return self._target

    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
        """Migrate an object, list, or union attribute, and the attributes it
        holds, to the target schema.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to migrate, on the source schema. Not changed.
        target: AttributeSchema
            The target schema of the migrator.

        Returns
        -------
        MigratedAttribute
            The attribute with the attributes it holds migrated, and what the
            value in effect lost.

        Raises
        ------
        ValueError
            If the target is not the target of the migrator, or an attribute
            held is not of the source schema.
        """
        if target.uid != self._target.uid:
            raise ValueError(
                f"Migrator of {self._source.tag} migrates to schema "
                f"{self._target.uid}, not {target.uid}."
            )
        effective_layer = self._effective_layer(attribute)
        update: dict[str, Any] = {"schema_uid": target.uid}
        lost: list[str] = []
        for layer in ("original_value", "updated_value", "mapped_value"):
            value, layer_lost = self._migrate_value(getattr(attribute, layer))
            update[layer] = value
            if layer == effective_layer:
                lost.extend(layer_lost)
        return MigratedAttribute(
            attribute.model_copy(update=update, deep=True),
            tuple(dict.fromkeys(lost)),
        )

    def attribute_migrators(
        self,
    ) -> Iterator[tuple[UUID, AttributeMigrator, AttributeSchema]]:
        """Iterate the migrators of the attribute schemas held, at any depth.

        Returns
        -------
        Iterator[tuple[UUID, AttributeMigrator, AttributeSchema]]
            The uid of each source attribute schema held, its migrator, and the
            target attribute schema it migrates to.
        """
        for pair in self._pairs.values():
            if pair is not None:
                yield from pair.attribute_migrators()

    def __eq__(self, other: object) -> bool:
        """Check if another migrator is a nested migrator between the same
        attribute schemas, migrating what they hold alike."""
        return (
            isinstance(other, NestedAttributeMigrator)
            and type(other) is type(self)
            and other._source.uid == self._source.uid
            and other._target.uid == self._target.uid
            and other._pairs == self._pairs
        )

    def __hash__(self) -> int:
        """Hash the migrator by its type and attribute schemas."""
        return hash((type(self), self._source.uid, self._target.uid))

    @staticmethod
    def held(schema: AttributeSchema) -> dict[str, AttributeSchema]:
        """Return the attribute schemas an attribute schema holds.

        Parameters
        ----------
        schema: AttributeSchema
            The attribute schema.

        Returns
        -------
        dict[str, AttributeSchema]
            The attribute schemas by key: their tag in an object, `[]` in a
            list, and `<index>` in a union; empty for any other schema.
        """
        if isinstance(schema, ObjectAttributeSchema):
            return dict(schema.attributes)
        if isinstance(schema, ListAttributeSchema):
            return {"[]": schema.attribute}
        if isinstance(schema, UnionAttributeSchema):
            return {
                f"<{index}>": member for index, member in enumerate(schema.attributes)
            }
        return {}

    @staticmethod
    def _effective_layer(attribute: AnyAttribute) -> str | None:
        """Find the value of the attribute in effect: the original, updated, or
        mapped one, or None."""
        value = attribute.value
        if value is None:
            return None
        return next(
            layer
            for layer in ("updated_value", "mapped_value", "original_value")
            if getattr(attribute, layer) is value
        )

    def _migrate_value(self, value: Any) -> tuple[Any, list[str]]:
        """Migrate the attributes one value holds, and return what they
        lost."""
        if value is None:
            return None, []
        if isinstance(self._source, ObjectAttributeSchema):
            migrated: dict[str, AnyAttribute] = {}
            lost: list[str] = []
            for key, nested in value.items():
                pair = self._pair_of_key(key, nested)
                if pair is None:
                    continue
                result = pair.migrate(nested)
                migrated[pair.target_key] = result.attribute
                lost.extend(result.lost)
            return migrated, lost
        if isinstance(self._source, ListAttributeSchema):
            pair = self._pairs.get("[]")
            results = [] if pair is None else [pair.migrate(nested) for nested in value]
            return (
                [result.attribute for result in results],
                [lost for result in results for lost in result.lost],
            )
        result = self._pair_of_member(value).migrate(value)
        return result.attribute, list(result.lost)

    def _pair_of_key(self, key: str, attribute: AnyAttribute) -> AttributePair | None:
        """Return the pair of an attribute held in an object by key, None where
        it is dropped.

        Raises
        ------
        ValueError
            If the key is not of the source schema.
        """
        if key not in self._pairs:
            raise ValueError(
                f"Attribute {attribute.uid} is held as {key!r}, which is not an "
                f"attribute of source schema {self._source.uid}."
            )
        return self._pairs[key]

    def _pair_of_member(self, attribute: AnyAttribute) -> AttributePair:
        """Return the pair of the union member of the attribute's schema.

        Raises
        ------
        ValueError
            If no pair is of the attribute's schema.
        """
        pair = next(
            (
                pair
                for pair in self._pairs.values()
                if pair is not None and pair.source.uid == attribute.schema_uid
            ),
            None,
        )
        if pair is None:
            raise ValueError(
                f"Attribute {attribute.uid} of schema {attribute.schema_uid} is not a "
                f"member of union {self._source.uid} with a member in union "
                f"{self._target.uid}."
            )
        return pair
