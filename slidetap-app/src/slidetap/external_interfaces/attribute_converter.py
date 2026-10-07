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

"""Converting an attribute whose values changed to the attribute schema of
another root."""

from abc import ABCMeta, abstractmethod
from collections.abc import Mapping
from enum import Enum

from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    EnumAttribute,
    RejectedValues,
)


class AttributeConverter(metaclass=ABCMeta):
    """Converts an attribute whose values changed to the attribute schema of the
    target root."""

    @abstractmethod
    def convert(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        """The attribute on the target schema, with its values converted.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to convert. Not changed.
        target: AttributeSchema
            The attribute schema of the target root to convert it to.

        Returns
        -------
        AnyAttribute
            The converted attribute, with the same uid. Without a value where
            the value it had has no counterpart on the target schema.
        """
        raise NotImplementedError()


class EnumAttributeConverter(AttributeConverter):
    """Converts the values of an enum attribute from one enum to another, value
    by value, through the member of the source enum to the member of the same
    name in the target enum.

    Only what does not follow the names is listed as an exception: a source
    member that became another target member, or that has no target member.
    A value without a target member is cleared.

    The original, updated, and mapped values are converted each on their own.
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
        """Create a converter between the values of two enums.

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
            member.value: self.convert_value(member.value)
            for member in self._source_type
        }

    def convert(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        if not isinstance(attribute, EnumAttribute):
            raise TypeError(f"Attribute {attribute.uid} is not an enum attribute.")
        rejected = attribute.rejected
        if attribute.value is not None and self.convert_value(attribute.value) is None:
            rejected |= self._below(attribute)
        return attribute.model_copy(
            update={
                "schema_uid": target.uid,
                "original_value": self.convert_value(attribute.original_value),
                "updated_value": self.convert_value(attribute.updated_value),
                "mapped_value": self.convert_value(attribute.mapped_value),
                "rejected": rejected,
            },
            deep=True,
        )

    def convert_value(self, value: str | None) -> str | None:
        """The target value of a source value, None for one without."""
        if value is None:
            return None
        try:
            member = self._source_type(value)
        except ValueError:
            # Not a value of the source enum either, so nothing to convert.
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


class ValueConverter(AttributeConverter):
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

    def convert(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
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
