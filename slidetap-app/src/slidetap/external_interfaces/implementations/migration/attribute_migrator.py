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
from collections.abc import Callable, Mapping, Sequence
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
    ListAttributeSchema,
    ObjectAttributeSchema,
    RejectedValues,
    UnionAttributeSchema,
)


class AttributeMigrator(metaclass=ABCMeta):
    """Migrates an attribute whose values changed to the attribute schema of the
    target root."""

    @abstractmethod
    def migrate(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        """The attribute on the target schema, with its values migrated.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to migrate. Not changed.
        target: AttributeSchema
            The attribute schema of the target root to migrate it to.

        Returns
        -------
        AnyAttribute
            The migrated attribute, with the same uid. Without a value where
            the value it had has no counterpart on the target schema.
        """
        raise NotImplementedError()


class UnchangedAttributeMigrator(AttributeMigrator):
    """Copies an attribute to a target attribute schema, for migrations.

    What an attribute holds is kept: its three values, what it was left to map,
    what was refused of it, and how it is shown. What refers to a schema is
    moved: the schema uid of the attribute, and of every attribute nested in
    the JSON of its values. A nested attribute is moved to the attribute of the
    same tag in an object, to the attribute of a list, and to the member of the
    same value type in a union.

    The mapping item is kept, as the mapper of an attribute a migration moves
    is moved with it, see SchemaMigration.migrate_attribute.

    A helper for implementing a migration, for the attributes whose values
    are the same on the target root.
    """

    def migrate(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        """The attribute, copied to the target schema.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to copy. Not changed.
        target: AttributeSchema
            The schema to copy it to, of the same value type.

        Returns
        -------
        AnyAttribute
            The copy, with the same uid.

        Raises
        ------
        ValueError
            If the target is of another value type, as the values of the
            attribute could not be held by it.
        """
        if attribute.attribute_value_type != self._value_type(target):
            raise ValueError(
                f"Cannot move attribute {attribute.uid} of value type "
                f"{attribute.attribute_value_type.name} to schema {target.uid} of "
                f"value type {self._value_type(target).name}."
            )
        update: dict[str, Any] = {
            "schema_uid": target.uid,
            "original_value": self._migrate_value(attribute.original_value, target),
            "updated_value": self._migrate_value(attribute.updated_value, target),
            "mapped_value": self._migrate_value(attribute.mapped_value, target),
        }
        return attribute.model_copy(update=update, deep=True)

    def _migrate_value(self, value: Any, target: AttributeSchema) -> Any:
        """A value of an attribute of the target schema, with what it nests
        moved to the target's nested schemas."""
        if value is None:
            return None
        if isinstance(target, ObjectAttributeSchema) and isinstance(value, Mapping):
            return {
                tag: self.migrate(nested, self._nested_of_object(target, tag))
                for tag, nested in value.items()
            }
        if isinstance(target, ListAttributeSchema) and isinstance(value, Sequence):
            return [self.migrate(nested, target.attribute) for nested in value]
        if isinstance(target, UnionAttributeSchema):
            return self.migrate(value, self._member_of_union(target, value))
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
    attribute is left without one: the values below it are refused, so that one
    of them does not take its place.
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

    def migrate(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        if not isinstance(attribute, EnumAttribute):
            raise TypeError(f"Attribute {attribute.uid} is not an enum attribute.")
        rejected = attribute.rejected
        if attribute.value is not None and self.migrate_value(attribute.value) is None:
            rejected |= self._below(attribute)
        return attribute.model_copy(
            update={
                "schema_uid": target.uid,
                "original_value": self.migrate_value(attribute.original_value),
                "updated_value": self.migrate_value(attribute.updated_value),
                "mapped_value": self.migrate_value(attribute.mapped_value),
                "rejected": rejected,
            },
            deep=True,
        )

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

    def migrate(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        return attribute.model_copy(
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
