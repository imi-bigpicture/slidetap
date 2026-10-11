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

"""Migrating attributes to the attribute schemas of another root.

The source has a sex, a string kept as it is, and a palette of tints that is
the same in the target under other uids. The target has a sex of other values.
"""

from enum import Enum
from typing import Any
from uuid import uuid4

import pytest

from slidetap.external_interfaces.implementations.migration import (
    EnumAttributeMigrator,
    FixedValueAttributeMigrator,
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    ListAttribute,
    ListAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    RejectedValues,
    StringAttribute,
    StringAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
)


class Sex(Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"


class TargetSex(Enum):
    MALE = "Male"
    FEMALE = "Female"


class Colour(Enum):
    RED = "Red"
    BLUE = "Blue"
    GREEN = "Green"
    NAVY = "Navy"


class TargetColour(Enum):
    RED = "RED"
    BLUE = "BLUE"
    GREEN = "GREEN"


COLOUR_MIGRATOR = EnumAttributeMigrator(
    Colour, TargetColour, {Colour.GREEN: None, Colour.NAVY: TargetColour.BLUE}
)
SEX_MIGRATOR = EnumAttributeMigrator(Sex, TargetSex)


class Schemas:
    """The attribute schemas of the source and the target root."""

    def __init__(self):
        self.sex = self._enum("sex", "Sex", Sex)
        self.target_sex = self._enum("sex", "Sex", TargetSex)
        self.label = self._string("label")
        self.shade = self._enum("shade", "Shade", Colour)
        self.target_shade = self._enum("shade", "Shade", Colour)
        self.tint = self._union("tint", self.label, self.shade)
        self.target_tint = self._union("tint", self.label, self.target_shade)
        self.tints = self._list("tints", self.tint)
        self.target_tints = self._list("tints", self.target_tint)
        self.palette = self._object("palette", self.tints)
        self.target_palette = self._object("palette", self.target_tints)
        self.kept = self._string("kept")

    @staticmethod
    def enum(schema: AttributeSchema, **values: Any) -> EnumAttribute:
        return EnumAttribute(uid=uuid4(), schema_uid=schema.uid, **values)

    @staticmethod
    def string(schema: AttributeSchema, value: str) -> StringAttribute:
        return StringAttribute(uid=uuid4(), schema_uid=schema.uid, original_value=value)

    def tints_value(self, label: str, shade: str) -> dict[str, AnyAttribute]:
        """The value of a palette: tints of a label and of a shade."""
        return {
            "tints": ListAttribute(
                uid=uuid4(),
                schema_uid=self.tints.uid,
                original_value=[
                    UnionAttribute(
                        uid=uuid4(),
                        schema_uid=self.tint.uid,
                        original_value=self.string(self.label, label),
                    ),
                    UnionAttribute(
                        uid=uuid4(),
                        schema_uid=self.tint.uid,
                        original_value=self.enum(self.shade, original_value=shade),
                    ),
                ],
            )
        }

    @staticmethod
    def _enum(tag: str, display_name: str, enum: type[Enum]) -> EnumAttributeSchema:
        return EnumAttributeSchema(
            uid=uuid4(),
            tag=tag,
            name=tag,
            display_name=display_name,
            optional=True,
            read_only=False,
            allowed_values=tuple(member.value for member in enum),
        )

    @staticmethod
    def _string(tag: str) -> StringAttributeSchema:
        return StringAttributeSchema(
            uid=uuid4(),
            tag=tag,
            name=tag,
            display_name=tag.capitalize(),
            optional=True,
            read_only=False,
        )

    @staticmethod
    def _object(tag: str, *attributes: AttributeSchema) -> ObjectAttributeSchema:
        return ObjectAttributeSchema(
            uid=uuid4(),
            tag=tag,
            name=tag,
            display_name=tag.capitalize(),
            optional=True,
            read_only=False,
            display_attributes_in_parent=False,
            display_value_tags=[],
            attributes={attribute.tag: attribute for attribute in attributes},  # type: ignore
        )

    @staticmethod
    def _list(tag: str, attribute: AttributeSchema) -> ListAttributeSchema:
        return ListAttributeSchema(
            uid=uuid4(),
            tag=tag,
            name=tag,
            display_name=tag.capitalize(),
            optional=True,
            read_only=False,
            display_attributes_in_parent=False,
            attribute=attribute,  # type: ignore
        )

    @staticmethod
    def _union(tag: str, *members: AttributeSchema) -> UnionAttributeSchema:
        return UnionAttributeSchema(
            uid=uuid4(),
            tag=tag,
            name=tag,
            display_name=tag.capitalize(),
            optional=True,
            read_only=False,
            attributes=members,  # type: ignore
        )


@pytest.fixture()
def schemas() -> Schemas:
    return Schemas()


@pytest.mark.unittest
class TestUnchangedAttributeMigrator:
    def test_an_attribute_is_moved_at_any_depth_in_every_value(self, schemas: Schemas):
        """Through an object, a list, and a union, in the original, updated, and
        mapped value, keeping what the attribute holds."""
        # Arrange
        mapping_item_uid = uuid4()
        palette = ObjectAttribute(
            uid=uuid4(),
            schema_uid=schemas.palette.uid,
            original_value=schemas.tints_value("original", "Red"),
            updated_value=schemas.tints_value("updated", "Blue"),
            mapped_value=schemas.tints_value("mapped", "Navy"),
            mappable_value="palette",
            mapping_item_uid=mapping_item_uid,
            rejected=RejectedValues.MAPPABLE,
        )

        # Act
        result = UnchangedAttributeMigrator().migrate(palette, schemas.target_palette)

        # Assert
        moved = result.attribute
        assert result.lost == ()
        assert moved.uid == palette.uid
        assert moved.schema_uid == schemas.target_palette.uid
        assert moved.mappable_value == "palette"
        assert moved.mapping_item_uid == mapping_item_uid
        assert moved.rejected == RejectedValues.MAPPABLE
        for layer, label, shade in (
            ("original_value", "original", "Red"),
            ("updated_value", "updated", "Blue"),
            ("mapped_value", "mapped", "Navy"),
        ):
            tints = getattr(moved, layer)["tints"]
            assert tints.schema_uid == schemas.target_tints.uid
            label_tint, shade_tint = tints.original_value
            assert label_tint.schema_uid == schemas.target_tint.uid
            assert label_tint.original_value.schema_uid == schemas.label.uid
            assert label_tint.original_value.original_value == label
            assert shade_tint.schema_uid == schemas.target_tint.uid
            assert shade_tint.original_value.schema_uid == schemas.target_shade.uid
            assert shade_tint.original_value.original_value == shade

    def test_another_value_type_is_refused(self, schemas: Schemas):
        # Arrange
        kept = schemas.string(schemas.kept, "kept")

        # Act & Assert
        with pytest.raises(ValueError, match="value type"):
            UnchangedAttributeMigrator().migrate(kept, schemas.target_sex)


@pytest.mark.unittest
class TestEnumAttributeMigrator:
    def test_values_are_migrated_by_name_with_the_exceptions(self):
        # Act
        values = COLOUR_MIGRATOR.values

        # Assert
        assert values == {"Red": "RED", "Blue": "BLUE", "Green": None, "Navy": "BLUE"}

    def test_each_value_is_migrated_on_its_own(self, schemas: Schemas):
        """And the values below one in effect with no target are refused, so
        that the attribute is left without a value, which is reported lost."""
        # Arrange
        attribute = schemas.enum(
            schemas.sex,
            original_value="M",
            updated_value="Other",
            mapped_value="F",
            mappable_value="female",
            mapping_item_uid=uuid4(),
        )

        # Act
        result = SEX_MIGRATOR.migrate(attribute, schemas.target_sex)

        # Assert
        migrated = result.attribute
        assert migrated.uid == attribute.uid
        assert migrated.schema_uid == schemas.target_sex.uid
        assert (
            migrated.original_value,
            migrated.updated_value,
            migrated.mapped_value,
        ) == ("Male", None, "Female")
        assert migrated.mappable_value == "female"
        assert migrated.mapping_item_uid == attribute.mapping_item_uid
        assert migrated.rejected == RejectedValues.ORIGINAL | RejectedValues.MAPPABLE
        assert migrated.value is None
        assert result.lost == ("'Other' is no longer an option of Sex.",)

    def test_a_value_lost_below_the_value_in_effect_is_not_reported(
        self, schemas: Schemas
    ):
        # Arrange
        attribute = schemas.enum(schemas.sex, original_value="Other", updated_value="M")

        # Act
        result = SEX_MIGRATOR.migrate(attribute, schemas.target_sex)

        # Assert
        assert result.lost == ()
        assert result.attribute.value == "Male"

    def test_a_value_not_of_the_source_enum_is_cleared(self, schemas: Schemas):
        # Arrange
        attribute = schemas.enum(schemas.sex, original_value="Unknown")

        # Act
        result = SEX_MIGRATOR.migrate(attribute, schemas.target_sex)

        # Assert
        assert result.attribute.original_value is None
        assert result.lost == ("'Unknown' is no longer an option of Sex.",)


@pytest.mark.unittest
class TestFixedValueAttributeMigrator:
    def test_the_value_is_set_whatever_the_attribute_held(self, schemas: Schemas):
        # Arrange
        kept = schemas.string(schemas.kept, "kept").model_copy(
            update={"updated_value": "edited", "rejected": RejectedValues.ORIGINAL}
        )

        # Act
        result = FixedValueAttributeMigrator("set").migrate(kept, schemas.kept)

        # Assert
        assert result.attribute.value == "set"
        assert result.attribute.updated_value is None
        assert result.attribute.rejected == RejectedValues.NONE
