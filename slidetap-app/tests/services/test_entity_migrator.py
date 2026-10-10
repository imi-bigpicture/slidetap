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

"""Migrating entities between two roots with explicit migrators.

The source being has a sex, a string kept as it is, one renamed, one dropped,
details holding a colour and a note, a palette of tints that is the same in
the target under other uids, and a private attribute. The target being has a
sex and a details colour of other values, the renamed string, and one that is
new.
"""

from collections.abc import Sequence
from enum import Enum
from typing import Any
from uuid import uuid4

import pytest

from slidetap.external_interfaces.implementations.migration import (
    AttributeMigrator,
    AttributeMigrators,
    EntityMigrator,
    EnumAttributeMigrator,
    FixedValueAttributeMigrator,
    MigratedAttribute,
    RootSchemaMigration,
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    DatasetSchema,
    EntityMigrationResult,
    EnumAttribute,
    EnumAttributeSchema,
    Item,
    ListAttribute,
    ListAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    ProjectSchema,
    RejectedValues,
    RootSchema,
    Sample,
    SampleSchema,
    StringAttribute,
    StringAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
    UnresolvedAttributeMigration,
)
from tests.conftest import MovingMigrator


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
    """The being of the source and the target root, and their roots."""

    def __init__(self):
        self.sex = self._enum("sex", "Sex", Sex)
        self.target_sex = self._enum("sex", "Sex", TargetSex)
        self.colour = self._enum("colour", "Colour", Colour)
        self.target_colour = self._enum("colour", "Colour", TargetColour)
        self.note = self._string("note")
        self.details = self._object("details", self.colour, self.note)
        self.target_details = self._object("details", self.target_colour, self.note)
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
        self.old_name = self._string("old_name")
        self.new_name = self._string("new_name")
        self.gone = self._string("gone")
        self.added = self._string("added")
        self.secret = self._string("secret")
        self.being_uid = uuid4()
        self.source = self._sample(
            [
                self.sex,
                self.kept,
                self.details,
                self.palette,
                self.old_name,
                self.gone,
            ],
            [self.secret],
        )
        self.target = self._sample(
            [
                self.target_sex,
                self.kept,
                self.target_details,
                self.target_palette,
                self.new_name,
                self.added,
            ],
            [self.secret],
        )

    def root(self, being: SampleSchema) -> RootSchema:
        return RootSchema(
            uid=uuid4(),
            name="root",
            project=ProjectSchema(uid=uuid4(), name="project", display_name="Project"),
            dataset=DatasetSchema(uid=uuid4(), name="dataset", display_name="Dataset"),
            samples={being.uid: being},
        )

    def being(
        self,
        private_attributes: dict[str, AnyAttribute] | None = None,
        **attributes: AnyAttribute,
    ) -> Sample:
        return Sample(
            uid=uuid4(),
            identifier="being",
            dataset_uid=uuid4(),
            batch_uid=uuid4(),
            schema_uid=self.being_uid,
            attributes=attributes,
            private_attributes=private_attributes or {},
        )

    @staticmethod
    def enum(schema: AttributeSchema, **values: Any) -> EnumAttribute:
        return EnumAttribute(uid=uuid4(), schema_uid=schema.uid, **values)

    @staticmethod
    def string(schema: AttributeSchema, value: str) -> StringAttribute:
        return StringAttribute(uid=uuid4(), schema_uid=schema.uid, original_value=value)

    def details_attribute(self, colour: str, **values: Any) -> ObjectAttribute:
        return ObjectAttribute(
            uid=uuid4(),
            schema_uid=self.details.uid,
            original_value={
                "colour": self.enum(self.colour, original_value=colour),
                "note": self.string(self.note, "a note"),
            },
            **values,
        )

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

    def _sample(
        self,
        attributes: list[AttributeSchema],
        private_attributes: list[AttributeSchema],
    ) -> SampleSchema:
        return SampleSchema(
            uid=self.being_uid,
            name="being",
            display_name="Being",
            display_order=0,
            attributes={attribute.tag: attribute for attribute in attributes},  # type: ignore
            private_attributes={
                attribute.tag: attribute  # type: ignore
                for attribute in private_attributes
            },
        )

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


class DetailsMigrator(AttributeMigrator):
    """Migrates the details: the colour by the colour migrator, the note as it
    is."""

    def __init__(self, schemas: Schemas):
        self._schemas = schemas
        self._unchanged = UnchangedAttributeMigrator()

    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
        return self._migrate_values(attribute, target, self._migrate_details)

    def _migrate_details(
        self, value: dict[str, AnyAttribute]
    ) -> tuple[dict[str, AnyAttribute], Sequence[str]]:
        migrated = dict(value)
        lost: tuple[str, ...] = ()
        if "colour" in value:
            colour = COLOUR_MIGRATOR.migrate(
                value["colour"], self._schemas.target_colour
            )
            migrated["colour"], lost = colour.attribute, colour.lost
        if "note" in value:
            migrated["note"] = self._unchanged.migrate(
                value["note"], self._schemas.note
            ).attribute
        return migrated, lost


class BeingMigrator(EntityMigrator[Item]):
    """Migrates the being, written out: the sex and the details by their
    migrators, the old name renamed, the gone attribute dropped, and the rest
    moved as it is."""

    def __init__(self, schemas: Schemas):
        super().__init__(schemas.source, schemas.target)
        self._schemas = schemas
        self.details_migrator = DetailsMigrator(schemas)

    def migrate(self, entity: Item) -> EntityMigrationResult:
        schemas = self._schemas
        attributes = self._move_all_except(
            entity.attributes, "sex", "details", "old_name", "gone"
        )
        if "sex" in entity.attributes:
            attributes["sex"] = self._migrate(
                entity.attributes["sex"], SEX_MIGRATOR, schemas.target_sex
            )
        if "details" in entity.attributes:
            attributes["details"] = self._migrate(
                entity.attributes["details"],
                self.details_migrator,
                schemas.target_details,
            )
        if "old_name" in entity.attributes:
            attributes["new_name"] = self._move(
                entity.attributes["old_name"], schemas.new_name
            )
        return EntityMigrationResult(
            schema_uid=self.target.uid,
            attributes=attributes,
            private_attributes=self._move_all_except(
                entity.private_attributes, private=True
            ),
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


@pytest.mark.unittest
class TestEntityMigrator:
    def test_a_migrator_must_write_out_its_migration(self, schemas: Schemas):
        # Act & Assert
        with pytest.raises(TypeError, match="abstract"):
            EntityMigrator[Item](schemas.source, schemas.target)  # type: ignore

    def test_every_attribute_is_moved_as_it_is_to_its_tag(self, schemas: Schemas):
        # Arrange
        source = schemas.source.model_copy(
            update={"attributes": {"kept": schemas.kept, "palette": schemas.palette}}
        )
        target = schemas.target.model_copy(
            update={
                "attributes": {"kept": schemas.kept, "palette": schemas.target_palette}
            }
        )
        kept = schemas.string(schemas.kept, "kept")
        secret = schemas.string(schemas.secret, "secret")
        palette = ObjectAttribute(
            uid=uuid4(),
            schema_uid=schemas.palette.uid,
            original_value=schemas.tints_value("label", "Red"),
        )
        being = schemas.being({"secret": secret}, kept=kept, palette=palette)

        # Act
        migrated = MovingMigrator[Item](source, target).migrate(being)

        # Assert
        assert migrated is not None
        assert migrated.schema_uid == target.uid
        assert migrated.attributes["kept"] == kept
        moved_palette = migrated.attributes["palette"]
        assert moved_palette.schema_uid == schemas.target_palette.uid
        assert migrated.private_attributes == {"secret": secret}

    def test_an_attribute_without_a_target_tag_is_refused(self, schemas: Schemas):
        # Arrange
        being = schemas.being(gone=schemas.string(schemas.gone, "gone"))

        # Act & Assert
        with pytest.raises(ValueError, match="'gone'"):
            MovingMigrator[Item](schemas.source, schemas.target).migrate(being)

    def test_attributes_are_moved_renamed_dropped_and_migrated(self, schemas: Schemas):
        # Arrange
        kept = schemas.string(schemas.kept, "kept")
        old_name = schemas.string(schemas.old_name, "named")
        being = schemas.being(
            sex=schemas.enum(schemas.sex, original_value="M"),
            kept=kept,
            details=schemas.details_attribute("Navy"),
            old_name=old_name,
            gone=schemas.string(schemas.gone, "gone"),
        )

        # Act
        migrated = BeingMigrator(schemas).migrate(being)

        # Assert
        assert migrated.attributes.keys() == {"sex", "kept", "details", "new_name"}
        assert migrated.attributes["sex"].value == "Male"
        assert migrated.attributes["kept"] == kept
        details = migrated.attributes["details"]
        assert details.schema_uid == schemas.target_details.uid
        assert details.original_value["colour"].value == "BLUE"
        assert details.original_value["note"].value == "a note"
        new_name = migrated.attributes["new_name"]
        assert new_name.uid == old_name.uid
        assert new_name.schema_uid == schemas.new_name.uid

    def test_a_value_with_no_target_leaves_the_attribute_unresolved(
        self, schemas: Schemas
    ):
        # Arrange
        sex = schemas.enum(schemas.sex, original_value="Other")
        being = schemas.being(sex=sex)

        # Act
        migrated = BeingMigrator(schemas).migrate(being)

        # Assert
        unresolved = migrated.attributes["sex"]
        assert isinstance(unresolved, UnresolvedAttributeMigration)
        assert unresolved.original == sex
        assert unresolved.proposed is not None
        assert unresolved.proposed.schema_uid == schemas.target_sex.uid
        assert unresolved.proposed.value is None
        assert unresolved.problem == "'Other' is no longer an option of Sex."

    def test_a_nested_value_with_no_target_leaves_the_attribute_unresolved(
        self, schemas: Schemas
    ):
        """With the rest of it migrated and proposed."""
        # Arrange
        being = schemas.being(details=schemas.details_attribute("Green"))

        # Act
        migrated = BeingMigrator(schemas).migrate(being)

        # Assert
        unresolved = migrated.attributes["details"]
        assert isinstance(unresolved, UnresolvedAttributeMigration)
        assert unresolved.problem == "'Green' is no longer an option of Colour."
        proposed = unresolved.proposed
        assert proposed is not None
        assert proposed.original_value["colour"].value is None
        assert proposed.original_value["note"].value == "a note"

    def test_a_nested_value_lost_below_the_value_in_effect_is_migrated(
        self, schemas: Schemas
    ):
        # Arrange
        details = schemas.details_attribute(
            "Green",
            updated_value={
                "colour": schemas.enum(schemas.colour, original_value="Red")
            },
        )
        being = schemas.being(details=details)

        # Act
        migrated = BeingMigrator(schemas).migrate(being)

        # Assert
        moved = migrated.attributes["details"]
        assert not isinstance(moved, UnresolvedAttributeMigration)
        assert moved.updated_value["colour"].value == "RED"
        assert moved.original_value["colour"].value is None


@pytest.mark.unittest
class TestAttributeMigrators:
    def test_a_registered_schema_gives_its_migrator_and_target(self, schemas: Schemas):
        # Arrange
        registry = AttributeMigrators([(schemas.sex, SEX_MIGRATOR, schemas.target_sex)])

        # Act
        found = registry.get(schemas.sex.uid)

        # Assert
        assert found == (SEX_MIGRATOR, schemas.target_sex)
        assert schemas.sex.uid in registry
        assert registry.get(schemas.kept.uid) is None

    def test_a_schema_given_twice_is_refused(self, schemas: Schemas):
        # Act & Assert
        with pytest.raises(ValueError, match="given twice"):
            AttributeMigrators(
                [
                    (schemas.sex, SEX_MIGRATOR, schemas.target_sex),
                    (schemas.sex, SEX_MIGRATOR, schemas.target_sex),
                ]
            )


class Migrations:
    """A root schema migration between the roots of the being."""

    @staticmethod
    def create(
        schemas: Schemas, item_migrators: Sequence[EntityMigrator[Item]] | None = None
    ) -> RootSchemaMigration:
        being_migrator = BeingMigrator(schemas)
        registry = AttributeMigrators(
            [
                (schemas.sex, SEX_MIGRATOR, schemas.target_sex),
                (
                    schemas.details,
                    being_migrator.details_migrator,
                    schemas.target_details,
                ),
                (schemas.colour, COLOUR_MIGRATOR, schemas.target_colour),
                (schemas.old_name, UnchangedAttributeMigrator(), schemas.new_name),
            ]
        )
        return RootSchemaMigration(
            schemas.root(schemas.source),
            schemas.root(schemas.target),
            registry,
            item_migrators=[being_migrator]
            if item_migrators is None
            else item_migrators,
        )


@pytest.mark.unittest
class TestRootSchemaMigration:
    def test_items_are_migrated_by_the_migrator_of_their_schema(self, schemas: Schemas):
        # Arrange
        migration = Migrations.create(schemas)
        being = schemas.being(sex=schemas.enum(schemas.sex, original_value="F"))

        # Act
        migrated = migration.migrate_item(being)

        # Assert
        assert migration.migrated_item_schemas == {schemas.being_uid}
        assert migrated is not None
        assert migrated.attributes["sex"].value == "Female"
        assert migration.migrate_item_schema(schemas.source) == schemas.target

    def test_the_project_and_dataset_without_migrator_are_the_same(
        self, schemas: Schemas
    ):
        # Arrange
        migration = Migrations.create(schemas)

        # Act & Assert
        assert migration.migrate_project(None) is None  # type: ignore
        assert migration.migrate_dataset(None) is None  # type: ignore

    def test_an_item_schema_without_migrator_is_refused(self, schemas: Schemas):
        # Arrange
        migration = Migrations.create(schemas, item_migrators=[])

        # Act & Assert
        assert migration.migrated_item_schemas == set()
        with pytest.raises(ValueError, match="not migrated"):
            migration.migrate_item(schemas.being())
        with pytest.raises(ValueError, match="not migrated"):
            migration.migrate_item_schema(schemas.source)

    def test_two_migrators_of_one_item_schema_are_refused(self, schemas: Schemas):
        # Act & Assert
        with pytest.raises(ValueError, match="Two migrators"):
            Migrations.create(
                schemas, item_migrators=[BeingMigrator(schemas), BeingMigrator(schemas)]
            )

    @pytest.mark.parametrize(("value", "expected"), [("M", "Male"), ("Other", None)])
    def test_the_attribute_of_a_mapping_item_is_migrated_by_its_migrator(
        self, schemas: Schemas, value: str, expected: str | None
    ):
        """One whose value has no target is returned without it."""
        # Arrange
        migration = Migrations.create(schemas)
        sex = schemas.enum(schemas.sex, original_value=value)

        # Act
        migrated = migration.migrate_attribute(sex)

        # Assert
        assert migrated is not None
        assert migrated.schema_uid == schemas.target_sex.uid
        assert migrated.original_value == expected

    def test_a_nested_attribute_of_a_mapping_item_is_migrated(self, schemas: Schemas):
        # Arrange
        migration = Migrations.create(schemas)
        colour = schemas.enum(schemas.colour, original_value="Navy")

        # Act
        migrated = migration.migrate_attribute(colour)

        # Assert
        assert migrated is not None
        assert migrated.schema_uid == schemas.target_colour.uid
        assert migrated.value == "BLUE"

    def test_an_attribute_the_target_root_has_is_moved_as_it_is(self, schemas: Schemas):
        # Arrange
        migration = Migrations.create(schemas)
        kept = schemas.string(schemas.kept, "kept")

        # Act
        migrated = migration.migrate_attribute(kept)

        # Assert
        assert migrated == kept

    def test_an_attribute_of_neither_is_not_migrated(self, schemas: Schemas):
        # Arrange
        migration = Migrations.create(schemas)

        # Act
        migrated = migration.migrate_attribute(schemas.string(schemas.gone, "gone"))

        # Assert
        assert migrated is None

    @pytest.mark.parametrize(
        ("source", "target"),
        [
            ("sex", "target_sex"),
            ("details", "target_details"),
            ("colour", "target_colour"),
            ("old_name", "new_name"),
            ("kept", "kept"),
            ("note", "note"),
            ("secret", "secret"),
            ("gone", None),
            ("palette", None),
        ],
    )
    def test_an_attribute_schema_gives_its_target_schema(
        self, schemas: Schemas, source: str, target: str | None
    ):
        """The registered target, the same schema where the target root has it,
        else none."""
        # Arrange
        migration = Migrations.create(schemas)

        # Act
        found = migration.migrate_attribute_schema(getattr(schemas, source))

        # Assert
        assert found == (None if target is None else getattr(schemas, target))
