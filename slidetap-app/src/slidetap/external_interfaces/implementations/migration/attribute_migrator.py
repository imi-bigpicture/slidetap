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
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast
from uuid import UUID

from slidetap.model import (
    AnyAttribute,
    AnyAttributeSchema,
    Attribute,
    AttributeSchema,
    AttributeValueType,
    EnumAttribute,
    EnumAttributeSchema,
    ListAttributeSchema,
    ObjectAttributeSchema,
    RejectedValues,
    UnionAttributeSchema,
)


@dataclass(frozen=True)
class MigratedAttribute:
    """An attribute migrated to the target schema."""

    attribute: AnyAttribute
    """The migrated attribute, with the same uid."""

    lost: tuple[str, ...] = ()
    """Why the value in effect lost values that have no counterpart on the
    target schema, empty where it lost none."""


class AttributeMigrator(metaclass=ABCMeta):
    """Migrates an attribute to the attribute schema of the target root."""

    @abstractmethod
    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
        """The attribute on the target schema, with its values migrated.

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
        """The attribute, copied to the target schema.

        Raises
        ------
        ValueError
            If the target is of another value type, as the values of the
            attribute could not be held by it.
        """
        return MigratedAttribute(self._move(attribute, target))

    def _move(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
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
        """A value of an attribute of the target schema, with what it nests
        moved to the target's nested schemas."""
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
        """The member a union's value is moved to: the one of its own schema
        where the target has it, else the first of its value type."""
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
        """The value type of a schema, which every concrete schema declares."""
        return cast(AnyAttributeSchema, schema).attribute_value_type

    @classmethod
    def without_mapping_items(
        cls, attribute: AnyAttribute, removed: Callable[[UUID], bool]
    ) -> AnyAttribute:
        """The attribute with the mapping items that are removed referred to by
        nothing, its own and those of the attributes nested in its values.

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
        return self._source_type

    @property
    def target_type(self) -> type[Enum]:
        return self._target_type

    @property
    def exceptions(self) -> Mapping[Enum, Enum | None]:
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

    def migrate_value(self, value: str | None) -> str | None:
        """The target value of a source value, None for one without."""
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
        """The values below the one in effect, which would be in effect if it
        were cleared."""
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
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
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


@dataclass(frozen=True)
class AttributePair:
    """A source attribute schema, the target attribute schema it becomes, and
    the migrator between them."""

    target_key: str
    """The key of the target among the attributes held with it."""

    source: AttributeSchema
    target: AttributeSchema
    migrator: AttributeMigrator

    def migrate(self, attribute: AnyAttribute) -> MigratedAttribute:
        return self.migrator.migrate(attribute, self.target)

    def attribute_migrator_of(
        self, schema_uid: UUID
    ) -> tuple[AttributeMigrator, AttributeSchema] | None:
        """The migrator of a source attribute schema and its target, of this
        pair or held by it."""
        if self.source.uid == schema_uid:
            return self.migrator, self.target
        if isinstance(self.migrator, NestedAttributeMigrator):
            return self.migrator.attribute_migrator_of(schema_uid)
        return None


class UndeclaredAttributesError(ValueError):
    """Source attributes that nothing is declared about but that cannot be
    moved as they are to the target schema."""

    def __init__(self, paths: Sequence[str]):
        self.paths = tuple(paths)
        super().__init__(
            f"Nothing is declared about {', '.join(self.paths)}, which cannot be "
            f"moved as it is to the target schema."
        )


class AttributeDeclarations:
    """What is declared about the attribute schemas of a source, by their uid:
    the migrator of those whose values changed, the target attribute schema of
    those renamed, and those dropped.

    Pairs source attribute schemas with target attribute schemas, building the
    migrator of each pair: the declared one, a `NestedAttributeMigrator` for an
    object, list, or union, or an `UnchangedAttributeMigrator`.
    """

    def __init__(
        self,
        migrated: Mapping[UUID, AttributeMigrator],
        renamed: Mapping[UUID, AttributeSchema],
        dropped: Collection[UUID],
    ):
        self._migrated = migrated
        self._renamed = renamed
        self._dropped = dropped
        self._unchanged = UnchangedAttributeMigrator()

    def pair(
        self,
        sources: Mapping[str, AttributeSchema],
        targets: Mapping[str, AttributeSchema],
        path_prefix: str = "",
    ) -> dict[str, AttributePair | None]:
        """The pair of every source attribute schema held by key, None for one
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
        """The key of the target attribute a source attribute becomes, None if
        it has none among the targets."""
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
        """Whether a source attribute cannot be moved as it is to the target: one
        of another kind, or an enum of other values."""
        if type(source) is not type(target):
            return True
        return (
            isinstance(source, EnumAttributeSchema)
            and isinstance(target, EnumAttributeSchema)
            and set(source.allowed_values) != set(target.allowed_values)
        )


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
        return self._source

    @property
    def target(self) -> AttributeSchema:
        return self._target

    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
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

    def attribute_migrator_of(
        self, schema_uid: UUID
    ) -> tuple[AttributeMigrator, AttributeSchema] | None:
        """The migrator of an attribute schema held at any depth, and the target
        attribute schema it migrates to, or None where it has none."""
        for pair in self._pairs.values():
            if pair is None:
                continue
            found = pair.attribute_migrator_of(schema_uid)
            if found is not None:
                return found
        return None

    @staticmethod
    def held(schema: AttributeSchema) -> dict[str, AttributeSchema]:
        """The attribute schemas a schema holds, by key: their tag in an object,
        `[]` in a list, and `<index>` in a union."""
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
        """The value of the attribute in effect: the original, updated, or
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
        """One value, with the attributes it holds migrated, and what they
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
        if key not in self._pairs:
            raise ValueError(
                f"Attribute {attribute.uid} is held as {key!r}, which is not an "
                f"attribute of source schema {self._source.uid}."
            )
        return self._pairs[key]

    def _pair_of_member(self, attribute: AnyAttribute) -> AttributePair:
        """The pair of the union member of the attribute's schema."""
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
