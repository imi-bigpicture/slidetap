#    Copyright 2024 SECTRA AB
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

"""Models for attributes that can be assigned to items."""

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from enum import Enum, IntFlag
from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    Self,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.code import Code
from slidetap.model.measurement import Measurement

AttributeType = TypeVar("AttributeType")


class RejectedValues(IntFlag):
    """What an item came in with that a curator has refused.

    Refusing is not correcting: it says the value is wrong and leaves no better
    one, which an empty `updated_value` cannot say — that means no edit was
    made. What is refused is kept as it was imported, so what a mapper produced
    can still be read when judging the mapper rather than the item.
    """

    NONE = 0
    ORIGINAL = 1
    """The value the item was imported with."""
    MAPPABLE = 2
    """The text mappers read. Refused, the attribute is left out of mapping, so
    re-running mappers neither replaces nor revives what was refused."""


class AttributeValueLayer(Enum):
    """One of the values an attribute holds, by the field holding it."""

    ORIGINAL = "original_value"
    """What the import said."""
    UPDATED = "updated_value"
    """What a curator has edited the attribute to."""
    MAPPED = "mapped_value"
    """What mapping made of the attribute."""


class Attribute(CamelCaseBaseModel, Generic[AttributeType]):
    """Base attribute class that all attribute types inherit from."""

    uid: UUID
    schema_uid: UUID
    original_value: AttributeType | None = None
    """What the import said. For an attribute holding other attributes, those
    attributes as they were imported, each keeping what it was imported with."""

    updated_value: AttributeType | None = None
    """What a curator has edited the attribute to."""

    mapped_value: AttributeType | None = None
    """What mapping made of the attribute.

    For an attribute holding other attributes this is either what its own
    mappable value mapped to, or the attributes it holds with the mappings
    that matched them applied — never both, since carrying a mappable value
    takes what it holds out of mapping (see `mappable_value`). Nothing where
    no mapping matched.
    """

    valid: bool = False
    display_value: str | None = None
    mappable_value: str | None = None
    """The value the import left for a mapping to resolve.

    An attribute carrying one is mapped as a whole, and mapping does not
    descend into it: where it holds other attributes, they are not mapped
    separately, and what it holds after mapping is what the mapping gave it.
    """

    mapping_item_uid: UUID | None = None
    rejected: RejectedValues = RejectedValues.NONE

    @property
    def value(self) -> AttributeType | None:
        """Return the effective value of the attribute, the value of
        `effective_layer`."""
        match self.effective_layer:
            case AttributeValueLayer.UPDATED:
                return self.updated_value
            case AttributeValueLayer.MAPPED:
                return self.mapped_value
            case AttributeValueLayer.ORIGINAL:
                return self.original_value
            case None:
                return None

    @property
    def effective_layer(self) -> AttributeValueLayer | None:
        """Which of the values of the attribute is its effective value, None
        where it has none.

        What was edited, else what was mapped, else what was imported — each of
        them only if it says something and has not been refused.
        """
        if self.updated_value is not None:
            return AttributeValueLayer.UPDATED
        if (
            self.mapped_value is not None
            and RejectedValues.MAPPABLE not in self.rejected
        ):
            return AttributeValueLayer.MAPPED
        if (
            self.original_value is not None
            and RejectedValues.ORIGINAL not in self.rejected
        ):
            return AttributeValueLayer.ORIGINAL
        return None

    @property
    def values_below_effective(self) -> RejectedValues:
        """The values below the effective value, which would take its place if
        it were cleared, as the refusals that keep them out.

        Below an edit are what was mapped and what was imported, and below what
        was mapped is what was imported. Below what was imported, or where
        there is no effective value, is nothing.
        """
        match self.effective_layer:
            case AttributeValueLayer.UPDATED:
                return RejectedValues.MAPPABLE | RejectedValues.ORIGINAL
            case AttributeValueLayer.MAPPED:
                return RejectedValues.ORIGINAL
            case _:
                return RejectedValues.NONE

    def without_mapping_items(self, removed: Callable[[UUID], bool]) -> Self:
        """Clear the references of the attribute to the mapping items that are
        removed, its own and those of the attributes nested in its values.

        Parameters
        ----------
        removed: Callable[[UUID], bool]
            Whether a mapping item is removed.

        Returns
        -------
        Self
            A copy, with what was mapped kept and the mapping item it was
            mapped by cleared where that is removed.
        """
        update: dict[str, Any] = {
            key: self._value_without_mapping_items(getattr(self, key), removed)
            for key in ("original_value", "updated_value", "mapped_value")
        }
        if self.mapping_item_uid is not None and removed(self.mapping_item_uid):
            update["mapping_item_uid"] = None
        return self.model_copy(update=update)

    @staticmethod
    def _value_without_mapping_items(
        value: Any, removed: Callable[[UUID], bool]
    ) -> Any:
        """Clear the references to removed mapping items of the attributes a
        value nests."""
        if isinstance(value, Attribute):
            return value.without_mapping_items(removed)
        if isinstance(value, Mapping):
            return {
                key: Attribute._value_without_mapping_items(nested, removed)
                for key, nested in value.items()
            }
        if isinstance(value, list | tuple):
            return [
                Attribute._value_without_mapping_items(nested, removed)
                for nested in value
            ]
        return value


class StringAttribute(Attribute[str]):
    """Attribute holding a string value."""

    attribute_value_type: Literal[AttributeValueType.STRING] = AttributeValueType.STRING


class EnumAttribute(Attribute[str]):
    """Attribute holding an enumerated string value."""

    attribute_value_type: Literal[AttributeValueType.ENUM] = AttributeValueType.ENUM


class DatetimeAttribute(Attribute[datetime]):
    """Attribute holding a datetime value."""

    attribute_value_type: Literal[AttributeValueType.DATETIME] = (
        AttributeValueType.DATETIME
    )


class NumericAttribute(Attribute[int | float]):
    """Attribute holding a numeric value (integer or float)."""

    attribute_value_type: Literal[AttributeValueType.NUMERIC] = (
        AttributeValueType.NUMERIC
    )


class MeasurementAttribute(Attribute[Measurement]):
    """Attribute holding a measurement value with unit."""

    attribute_value_type: Literal[AttributeValueType.MEASUREMENT] = (
        AttributeValueType.MEASUREMENT
    )


class CodeAttribute(Attribute[Code]):
    """Attribute holding a coded value with scheme."""

    attribute_value_type: Literal[AttributeValueType.CODE] = AttributeValueType.CODE


class BooleanAttribute(Attribute[bool]):
    """Attribute holding a boolean value."""

    attribute_value_type: Literal[AttributeValueType.BOOLEAN] = (
        AttributeValueType.BOOLEAN
    )


class ObjectAttribute(
    Attribute[
        dict[
            str,
            Annotated[
                Union[
                    StringAttribute,
                    EnumAttribute,
                    DatetimeAttribute,
                    NumericAttribute,
                    MeasurementAttribute,
                    CodeAttribute,
                    BooleanAttribute,
                    "ObjectAttribute",
                    "ListAttribute",
                    "UnionAttribute",
                ],
                Field(discriminator="attribute_value_type"),
            ],
        ]
    ]
):
    """Attribute holding a dictionary of other attributes."""

    attribute_value_type: Literal[AttributeValueType.OBJECT] = AttributeValueType.OBJECT


class ListAttribute(
    Attribute[
        Sequence[
            Annotated[
                Union[
                    StringAttribute,
                    EnumAttribute,
                    DatetimeAttribute,
                    NumericAttribute,
                    MeasurementAttribute,
                    CodeAttribute,
                    BooleanAttribute,
                    ObjectAttribute,
                    "ListAttribute",
                    "UnionAttribute",
                ],
                Field(discriminator="attribute_value_type"),
            ]
        ]
    ]
):
    """Attribute holding a list of other attributes."""

    attribute_value_type: Literal[AttributeValueType.LIST] = AttributeValueType.LIST


class UnionAttribute(
    Attribute[
        Annotated[
            Union[
                StringAttribute,
                EnumAttribute,
                DatetimeAttribute,
                NumericAttribute,
                MeasurementAttribute,
                CodeAttribute,
                BooleanAttribute,
                ObjectAttribute,
                ListAttribute,
                "UnionAttribute",
            ],
            Field(discriminator="attribute_value_type"),
        ]
    ]
):
    """Attribute that can hold different types of attributes.

    UnionAttribute value is a tuple of a string that defines the schema and an
    AttributeValue.
    """

    attribute_value_type: Literal[AttributeValueType.UNION] = AttributeValueType.UNION


AnyAttribute = Annotated[
    StringAttribute
    | EnumAttribute
    | DatetimeAttribute
    | NumericAttribute
    | MeasurementAttribute
    | CodeAttribute
    | BooleanAttribute
    | ObjectAttribute
    | ListAttribute
    | UnionAttribute,
    Field(discriminator="attribute_value_type"),
]


def attribute_factory(data: dict[str, Any]) -> AnyAttribute:
    attribute_value_type = AttributeValueType(data.pop("attributeValueType"))
    if attribute_value_type == AttributeValueType.STRING:
        return StringAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.ENUM:
        return EnumAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.DATETIME:
        return DatetimeAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.NUMERIC:
        return NumericAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.MEASUREMENT:
        return MeasurementAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.CODE:
        return CodeAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.BOOLEAN:
        return BooleanAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.OBJECT:
        return ObjectAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.LIST:
        return ListAttribute.model_validate(data)
    if attribute_value_type == AttributeValueType.UNION:
        return UnionAttribute.model_validate(data)
    raise ValueError(
        f"Unknown item attribute_value_type: {data.get('attribute_value_type')}"
    ) from None
