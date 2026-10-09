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
from dataclasses import dataclass
from enum import Enum
from typing import Any

from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    EnumAttribute,
    RejectedValues,
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

    @staticmethod
    def _migrate_values(
        attribute: AnyAttribute,
        target: AttributeSchema,
        migrate_value: Callable[[Any], tuple[Any, Sequence[str]]],
    ) -> MigratedAttribute:
        """Copy an attribute to the target schema, with its original, updated,
        and mapped values each migrated on its own.

        For a migrator of an object, list, or union attribute that migrates
        the attributes its values hold. What the attribute was left to map,
        what was refused of it, how it is shown, and its mapping item are kept.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to migrate. Not changed.
        target: AttributeSchema
            The attribute schema of the target root to migrate it to.
        migrate_value: Callable[[Any], tuple[Any, Sequence[str]]]
            Migrates one value that is not None, and tells what it lost.

        Returns
        -------
        MigratedAttribute
            The attribute with its values migrated, and what the value in
            effect lost.
        """
        update: dict[str, Any] = {"schema_uid": target.uid}
        lost: list[str] = []
        effective = AttributeMigrator._effective_layer(attribute)
        for layer in ("original_value", "updated_value", "mapped_value"):
            value = getattr(attribute, layer)
            if value is None:
                update[layer] = None
                continue
            update[layer], layer_lost = migrate_value(value)
            if layer == effective:
                lost.extend(layer_lost)
        return MigratedAttribute(
            attribute.model_copy(update=update, deep=True),
            tuple(dict.fromkeys(lost)),
        )

    @staticmethod
    def _effective_layer(attribute: AnyAttribute) -> str | None:
        """Find which value of an attribute is in effect, as `value` gives it:
        the updated, the mapped, or the original one, or None."""
        if attribute.updated_value is not None:
            return "updated_value"
        if (
            attribute.mapped_value is not None
            and RejectedValues.MAPPABLE not in attribute.rejected
        ):
            return "mapped_value"
        if (
            attribute.original_value is not None
            and RejectedValues.ORIGINAL not in attribute.rejected
        ):
            return "original_value"
        return None


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
