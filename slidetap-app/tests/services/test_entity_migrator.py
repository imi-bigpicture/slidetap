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

"""Migrating entities between two roots with declared migrators.

The source being has a sex, a colour nested in an object, in a list, and in a
union, an attribute renamed, one dropped, one kept as it is, and a private
attribute; the target being has a sex and colours of other values, the renamed
attribute, and one that is new.
"""

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import pytest

from slidetap.external_interfaces.implementations.migration import (
    DeclarativeSchemaMigration,
    EntityMigrator,
    EnumAttributeMigrator,
    FixedValueAttributeMigrator,
    NestedAttributeMigrator,
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


class Schemas:
    """The being of the source and the target root, and their roots."""

    def __init__(self):
        self.sex = self._enum("sex", "Sex", Sex)
        self.target_sex = self._enum("sex", "Sex", TargetSex)
        self.colour = self._enum("colour", "Colour", Colour)
        self.target_colour = self._enum("colour", "Colour", TargetColour)
        self.list_colour = self._enum("colour", "Colour", Colour)
        self.target_list_colour = self._enum("colour", "Colour", TargetColour)
        self.shade = self._enum("shade", "Shade", Colour)
        self.target_shade = self._enum("shade", "Shade", TargetColour)
        self.note = self._string("note")
        self.label = self._string("label")
        self.kept = self._string("kept")
        self.old_name = self._string("old_name")
        self.new_name = self._string("new_name")
        self.gone = self._string("gone")
        self.added = self._string("added")
        self.secret = self._string("secret")
        self.details = self._object("details", self.colour, self.note)
        self.target_details = self._object("details", self.target_colour, self.note)
        self.colours = self._list("colours", self.list_colour)
        self.target_colours = self._list("colours", self.target_list_colour)
        self.tint = self._union("tint", self.label, self.shade)
        self.target_tint = self._union("tint", self.label, self.target_shade)
        self.being_uid = uuid4()
        self.source = self._sample(
            [
                self.sex,
                self.kept,
                self.details,
                self.colours,
                self.tint,
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
                self.target_colours,
                self.target_tint,
                self.new_name,
                self.added,
            ],
            [self.secret],
        )

    def migrator(self, **declared: Any) -> EntityMigrator[Item]:
        """The migrator of the being, declaring every change unless given."""
        arguments = self.migrator_declarations()
        arguments.update(declared)
        return EntityMigrator[Item](self.source, self.target, **arguments)

    def migrator_declarations(self) -> dict[str, Any]:
        """What the migrator of the being declares about every change."""
        colours = EnumAttributeMigrator(
            Colour,
            TargetColour,
            {Colour.GREEN: None, Colour.NAVY: TargetColour.BLUE},
        )
        return {
            "migrated_attributes": [
                (self.sex, EnumAttributeMigrator(Sex, TargetSex)),
                (self.colour, colours),
                (self.list_colour, colours),
                (self.shade, colours),
            ],
            "renamed_attributes": [(self.old_name, self.new_name)],
            "dropped_attributes": [self.gone],
        }

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

    def details_value(self, colour: str) -> dict[str, AnyAttribute]:
        return {
            "colour": self.enum(self.colour, original_value=colour),
            "note": self.string(self.note, "a note"),
        }

    def details_attribute(self, colour: str) -> ObjectAttribute:
        return ObjectAttribute(
            uid=uuid4(),
            schema_uid=self.details.uid,
            original_value=self.details_value(colour),
        )

    def colours_attribute(self, *colours: str) -> ListAttribute:
        return ListAttribute(
            uid=uuid4(),
            schema_uid=self.colours.uid,
            original_value=[
                self.enum(self.list_colour, original_value=colour) for colour in colours
            ],
        )

    def tint_attribute(self, member: AnyAttribute) -> UnionAttribute:
        return UnionAttribute(
            uid=uuid4(), schema_uid=self.tint.uid, original_value=member
        )

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


@pytest.fixture()
def schemas() -> Schemas:
    return Schemas()


@pytest.mark.unittest
class TestEntityMigrator:
    @staticmethod
    def _unresolved(
        migrated: EntityMigrationResult,
    ) -> dict[str, UnresolvedAttributeMigration]:
        """Get the unresolved attributes of a result, public and private, by tag."""
        return {
            tag: attribute
            for tag, attribute in (
                *migrated.attributes.items(),
                *migrated.private_attributes.items(),
            )
            if isinstance(attribute, UnresolvedAttributeMigration)
        }

    def test_attributes_are_moved_renamed_dropped_and_migrated(self, schemas: Schemas):
        # Arrange
        kept = schemas.string(schemas.kept, "kept")
        old_name = schemas.string(schemas.old_name, "named")
        being = schemas.being(
            sex=schemas.enum(schemas.sex, original_value="M"),
            kept=kept,
            details=schemas.details_attribute("Navy"),
            colours=schemas.colours_attribute("Red", "Blue"),
            old_name=old_name,
            gone=schemas.string(schemas.gone, "gone"),
        )

        # Act
        migrated = schemas.migrator().migrate(being)

        # Assert
        assert migrated.schema_uid == schemas.target.uid
        assert self._unresolved(migrated) == {}
        attributes = migrated.attributes
        assert attributes.keys() == {"sex", "kept", "details", "colours", "new_name"}
        assert attributes["sex"].schema_uid == schemas.target_sex.uid
        assert attributes["sex"].value == "Male"
        assert attributes["kept"] == kept
        assert attributes["new_name"].uid == old_name.uid
        assert attributes["new_name"].schema_uid == schemas.new_name.uid
        details = attributes["details"]
        assert details.schema_uid == schemas.target_details.uid
        assert details.original_value["colour"].schema_uid == (
            schemas.target_colour.uid
        )
        assert details.original_value["colour"].value == "BLUE"
        assert details.original_value["note"].value == "a note"
        colours = attributes["colours"]
        assert colours.schema_uid == schemas.target_colours.uid
        assert [colour.value for colour in colours.original_value] == ["RED", "BLUE"]
        assert [colour.schema_uid for colour in colours.original_value] == [
            schemas.target_list_colour.uid
        ] * 2

    def test_a_private_attribute_is_moved(self, schemas: Schemas):
        # Arrange
        secret = schemas.string(schemas.secret, "secret")

        # Act
        migrated = schemas.migrator().migrate(
            schemas.being(private_attributes={"secret": secret})
        )

        # Assert
        assert migrated.attributes == {}
        assert migrated.private_attributes == {"secret": secret}

    @pytest.mark.parametrize(
        ("member", "expected_schema", "expected_value"),
        [("shade", "target_shade", "BLUE"), ("label", "label", "a label")],
    )
    def test_a_union_member_is_migrated_to_the_member_of_its_position(
        self,
        schemas: Schemas,
        member: str,
        expected_schema: str,
        expected_value: str,
    ):
        # Arrange
        value = (
            schemas.enum(schemas.shade, original_value="Navy")
            if member == "shade"
            else schemas.string(schemas.label, "a label")
        )

        # Act
        migrated = schemas.migrator().migrate(
            schemas.being(tint=schemas.tint_attribute(value))
        )

        # Assert
        tint = migrated.attributes["tint"]
        assert tint.schema_uid == schemas.target_tint.uid
        assert tint.original_value.uid == value.uid
        assert tint.original_value.schema_uid == (getattr(schemas, expected_schema).uid)
        assert tint.original_value.value == expected_value

    def test_a_nested_attribute_is_renamed(self, schemas: Schemas):
        # Arrange
        remark = schemas._string("remark")
        target_details = schemas._object("details", schemas.target_colour, remark)
        target = schemas.target.model_copy(
            update={
                "attributes": {
                    **schemas.target.attributes,
                    "details": target_details,
                }
            }
        )
        source_details = schemas.details_attribute("Red")
        migrator = EntityMigrator[Item](
            schemas.source,
            target,
            **{
                **schemas.migrator_declarations(),
                "renamed_attributes": [
                    (schemas.old_name, schemas.new_name),
                    (schemas.note, remark),
                ],
            },
        )

        # Act
        migrated = migrator.migrate(schemas.being(details=source_details))

        # Assert
        details = migrated.attributes["details"].original_value
        assert details.keys() == {"colour", "remark"}
        assert details["remark"].uid == source_details.original_value["note"].uid
        assert details["remark"].schema_uid == remark.uid
        assert details["remark"].value == "a note"

    def test_a_value_with_no_target_leaves_the_attribute_unresolved(
        self, schemas: Schemas
    ):
        # Arrange
        sex = schemas.enum(schemas.sex, original_value="Other")
        being = schemas.being(sex=sex)

        # Act
        migrated = schemas.migrator().migrate(being)

        # Assert
        unresolved = self._unresolved(migrated)["sex"]
        assert unresolved.original == sex
        assert unresolved.proposed is not None
        assert unresolved.proposed.uid == sex.uid
        assert unresolved.proposed.schema_uid == schemas.target_sex.uid
        assert unresolved.proposed.value is None
        assert unresolved.problem == "'Other' is no longer an option of Sex."

    def test_a_nested_value_with_no_target_leaves_the_top_attribute_unresolved(
        self, schemas: Schemas
    ):
        """With what could be migrated proposed, and each problem once."""
        # Arrange
        details = schemas.details_attribute("Green")
        colours = schemas.colours_attribute("Red", "Green", "Green")
        being = schemas.being(details=details, colours=colours)

        # Act
        migrated = schemas.migrator().migrate(being)

        # Assert
        assert migrated.attributes.keys() == {"details", "colours"}
        assert self._unresolved(migrated).keys() == {"details", "colours"}
        proposed_details = self._unresolved(migrated)["details"].proposed
        assert proposed_details is not None
        assert proposed_details.schema_uid == schemas.target_details.uid
        assert proposed_details.original_value["colour"].value is None
        assert proposed_details.original_value["note"].value == "a note"
        proposed_colours = self._unresolved(migrated)["colours"].proposed
        assert proposed_colours is not None
        assert [colour.value for colour in proposed_colours.original_value] == [
            "RED",
            None,
            None,
        ]
        assert self._unresolved(migrated)["colours"].problem == (
            "'Green' is no longer an option of Colour."
        )

    def test_a_value_with_no_target_that_is_not_in_effect_is_migrated(
        self, schemas: Schemas
    ):
        # Arrange
        being = schemas.being(
            sex=schemas.enum(schemas.sex, original_value="Other", updated_value="F")
        )

        # Act
        migrated = schemas.migrator().migrate(being)

        # Assert
        assert self._unresolved(migrated) == {}
        sex = migrated.attributes["sex"]
        assert (sex.original_value, sex.value) == (None, "Female")

    def test_a_nested_value_lost_below_the_value_in_effect_is_migrated(
        self, schemas: Schemas
    ):
        # Arrange
        details = schemas.details_attribute("Green").model_copy(
            update={"updated_value": schemas.details_value("Red")}
        )

        # Act
        migrated = schemas.migrator().migrate(schemas.being(details=details))

        # Assert
        assert self._unresolved(migrated) == {}
        migrated_details = migrated.attributes["details"]
        assert migrated_details.original_value["colour"].value is None
        assert migrated_details.updated_value["colour"].value == "RED"

    def test_a_fixed_value_migrator_sets_its_value(self, schemas: Schemas):
        # Arrange
        migrator = schemas.migrator(
            migrated_attributes=[
                *schemas.migrator_declarations()["migrated_attributes"],
                (schemas.kept, FixedValueAttributeMigrator("set")),
            ]
        )
        being = schemas.being(kept=schemas.string(schemas.kept, "kept"))

        # Act
        migrated = migrator.migrate(being)

        # Assert
        assert migrated.attributes["kept"].value == "set"

    @pytest.mark.parametrize(
        ("source", "target", "migrator_type"),
        [
            ("sex", "target_sex", EnumAttributeMigrator),
            ("kept", "kept", UnchangedAttributeMigrator),
            ("details", "target_details", NestedAttributeMigrator),
            ("colour", "target_colour", EnumAttributeMigrator),
            ("note", "note", UnchangedAttributeMigrator),
            ("colours", "target_colours", NestedAttributeMigrator),
            ("list_colour", "target_list_colour", EnumAttributeMigrator),
            ("tint", "target_tint", NestedAttributeMigrator),
            ("shade", "target_shade", EnumAttributeMigrator),
            ("old_name", "new_name", UnchangedAttributeMigrator),
            ("secret", "secret", UnchangedAttributeMigrator),
        ],
    )
    def test_the_attribute_migrators_reach_every_depth(
        self, schemas: Schemas, source: str, target: str, migrator_type: type
    ):
        # Act
        found = {
            uid: (migrator, target_schema)
            for uid, migrator, target_schema in schemas.migrator().attribute_migrators()
        }

        # Assert
        migrator, target_schema = found[getattr(schemas, source).uid]
        assert isinstance(migrator, migrator_type)
        assert target_schema == getattr(schemas, target)

    @pytest.mark.parametrize("schema", ["gone", "added", "target_sex"])
    def test_a_dropped_or_target_attribute_has_no_attribute_migrator(
        self, schemas: Schemas, schema: str
    ):
        # Act
        uids = [uid for uid, _, _ in schemas.migrator().attribute_migrators()]

        # Assert
        assert getattr(schemas, schema).uid not in uids

    def test_an_undeclared_change_is_refused(self, schemas: Schemas):
        """An enum of other values, at any depth, and an attribute the target
        has no tag for."""
        # Act & Assert
        with pytest.raises(ValueError, match="says nothing about") as error:
            schemas.migrator(migrated_attributes=[], dropped_attributes=[])
        message = str(error.value)
        for path in ("sex", "details/colour", "colours[]", "tint<1>", "gone"):
            assert path in message

    def test_an_attribute_of_another_kind_is_refused(self, schemas: Schemas):
        # Arrange
        target = schemas.target.model_copy(
            update={
                "attributes": {
                    **schemas.target.attributes,
                    "kept": schemas.target_sex.model_copy(
                        update={"uid": uuid4(), "tag": "kept"}
                    ),
                }
            }
        )

        # Act & Assert
        with pytest.raises(ValueError, match="says nothing about kept"):
            EntityMigrator[Item](
                schemas.source, target, **schemas.migrator_declarations()
            )

    def test_a_private_attribute_without_target_is_refused(self, schemas: Schemas):
        # Arrange
        target = schemas.target.model_copy(update={"private_attributes": {}})

        # Act & Assert
        with pytest.raises(ValueError, match="says nothing about !secret"):
            EntityMigrator[Item](
                schemas.source, target, **schemas.migrator_declarations()
            )

    def test_a_rename_to_another_object_is_refused(self, schemas: Schemas):
        """The nested note cannot become a top-level attribute."""
        # Act & Assert
        with pytest.raises(ValueError, match="says nothing about details/note"):
            schemas.migrator(
                renamed_attributes=[
                    (schemas.old_name, schemas.new_name),
                    (schemas.note, schemas.added),
                ]
            )

    @pytest.mark.parametrize(
        "declaration", ["migrated", "renamed", "renamed to", "dropped"]
    )
    def test_a_declaration_not_of_the_schemas_is_refused(
        self, schemas: Schemas, declaration: str
    ):
        """Migrated, renamed and dropped are of the source, renamed to of the
        target."""
        # Arrange
        foreign = {
            "migrated": {
                "migrated_attributes": [
                    (schemas.target_sex, FixedValueAttributeMigrator("M"))
                ]
            },
            "renamed": {"renamed_attributes": [(schemas.new_name, schemas.new_name)]},
            "renamed to": {
                "renamed_attributes": [(schemas.old_name, schemas.old_name)]
            },
            "dropped": {"dropped_attributes": [schemas.gone, schemas.added]},
        }[declaration]

        # Act & Assert
        with pytest.raises(ValueError, match=f"as {declaration}"):
            schemas.migrator(**foreign)

    def test_an_attribute_declared_twice_is_refused(self, schemas: Schemas):
        # Act & Assert
        with pytest.raises(ValueError, match="gone .* as dropped more than once"):
            schemas.migrator(dropped_attributes=[schemas.gone, schemas.gone])


@pytest.mark.unittest
class TestEnumAttributeMigrator:
    def test_values_are_migrated_by_name_with_the_exceptions(self):
        # Arrange
        migrator = EnumAttributeMigrator(
            Colour, TargetColour, {Colour.GREEN: None, Colour.NAVY: TargetColour.BLUE}
        )

        # Act
        values = migrator.values

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
        result = EnumAttributeMigrator(Sex, TargetSex).migrate(
            attribute, schemas.target_sex
        )

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
        result = EnumAttributeMigrator(Sex, TargetSex).migrate(
            attribute, schemas.target_sex
        )

        # Assert
        assert result.lost == ()
        assert result.attribute.value == "Male"

    def test_a_value_not_of_the_source_enum_is_cleared(self, schemas: Schemas):
        # Arrange
        attribute = schemas.enum(schemas.sex, original_value="Unknown")

        # Act
        result = EnumAttributeMigrator(Sex, TargetSex).migrate(
            attribute, schemas.target_sex
        )

        # Assert
        assert result.attribute.original_value is None
        assert result.lost == ("'Unknown' is no longer an option of Sex.",)


@pytest.mark.unittest
class TestDeclarativeSchemaMigration:
    def test_an_item_schema_of_both_roots_gets_a_plain_migrator(self, schemas: Schemas):
        # Arrange
        unchanged = schemas.source.model_copy(
            update={"attributes": {"kept": schemas.kept}, "private_attributes": {}}
        )
        root = schemas.root(unchanged)
        kept = schemas.string(schemas.kept, "kept")

        # Act
        migration = DeclarativeSchemaMigration(root, root)

        # Assert
        migrated = migration.migrate_item(schemas.being(kept=kept))
        assert migrated.schema_uid == unchanged.uid
        assert migrated.attributes == {"kept": kept}
        assert migration.migrate_item_schema(unchanged) == unchanged

    def test_a_plain_migrator_of_a_changed_item_schema_is_refused(
        self, schemas: Schemas
    ):
        # Act & Assert
        with pytest.raises(ValueError, match="says nothing about"):
            DeclarativeSchemaMigration(
                schemas.root(schemas.source), schemas.root(schemas.target)
            )

    def test_an_item_schema_without_target_or_migrator_is_refused(
        self, schemas: Schemas
    ):
        # Arrange
        target = schemas.root(schemas.target.model_copy(update={"uid": uuid4()}))

        # Act & Assert
        with pytest.raises(ValueError, match="has no migrator"):
            DeclarativeSchemaMigration(schemas.root(schemas.source), target)

    def test_two_migrators_of_one_item_schema_are_refused(self, schemas: Schemas):
        # Act & Assert
        with pytest.raises(ValueError, match="Two migrators"):
            DeclarativeSchemaMigration(
                schemas.root(schemas.source),
                schemas.root(schemas.target),
                item_migrators=[schemas.migrator(), schemas.migrator()],
            )

    def test_items_are_migrated_by_their_migrator(self, schemas: Schemas):
        # Arrange
        migration = self._migration(schemas)
        being = schemas.being(sex=schemas.enum(schemas.sex, original_value="F"))

        # Act
        migrated = migration.migrate_item(being)

        # Assert
        assert migrated.attributes["sex"].value == "Female"
        with pytest.raises(ValueError, match="not an item schema"):
            migration.migrate_item(being.model_copy(update={"schema_uid": uuid4()}))

    def test_an_item_schema_gives_the_target_item_schema_of_its_migrator(
        self, schemas: Schemas
    ):
        # Arrange
        migration = self._migration(schemas)
        unknown = schemas.source.model_copy(update={"uid": uuid4()})

        # Act
        target = migration.migrate_item_schema(schemas.source)

        # Assert
        assert target == schemas.target
        with pytest.raises(ValueError, match="not an item schema"):
            migration.migrate_item_schema(unknown)

    @pytest.mark.parametrize(
        ("attribute_name", "value", "expected"),
        [
            ("sex", "M", "Male"),
            ("colour", "Navy", "BLUE"),
            ("list_colour", "Green", None),
            ("shade", "Red", "RED"),
        ],
    )
    def test_an_attribute_at_any_depth_is_migrated_for_a_mapper(
        self,
        schemas: Schemas,
        attribute_name: str,
        value: str,
        expected: str | None,
    ):
        """One whose value has no target is returned without it."""
        # Arrange
        migration = self._migration(schemas)
        attribute = schemas.enum(getattr(schemas, attribute_name), original_value=value)

        # Act
        migrated = migration.migrate_attribute(attribute)

        # Assert
        assert migrated is not None
        assert migrated.uid == attribute.uid
        assert migrated.schema_uid == (getattr(schemas, f"target_{attribute_name}").uid)
        assert migrated.original_value == expected

    def test_an_object_attribute_is_migrated_for_a_mapper(self, schemas: Schemas):
        # Arrange
        migration = self._migration(schemas)
        attribute = schemas.details_attribute("Navy")

        # Act
        migrated = migration.migrate_attribute(attribute)

        # Assert
        assert migrated is not None
        assert migrated.schema_uid == schemas.target_details.uid
        assert migrated.original_value["colour"].value == "BLUE"

    @pytest.mark.parametrize(
        ("source_name", "target_name"),
        [
            ("kept", "kept"),
            ("sex", "target_sex"),
            ("old_name", "new_name"),
            ("details", "target_details"),
            ("colour", "target_colour"),
            ("list_colour", "target_list_colour"),
            ("shade", "target_shade"),
        ],
    )
    def test_an_attribute_schema_at_any_depth_gives_its_target_schema(
        self, schemas: Schemas, source_name: str, target_name: str
    ):
        """Kept, moved, renamed, and nested in an object, a list, or a union."""
        # Arrange
        migration = self._migration(schemas)

        # Act
        target = migration.migrate_attribute_schema(getattr(schemas, source_name))

        # Assert
        assert target == getattr(schemas, target_name)

    @pytest.mark.parametrize("dropped", [True, False])
    def test_a_dropped_or_unknown_attribute_schema_has_no_target_schema(
        self, schemas: Schemas, dropped: bool
    ):
        # Arrange
        migration = self._migration(schemas)
        schema = schemas.gone if dropped else schemas.added

        # Act & Assert
        assert migration.migrate_attribute_schema(schema) is None

    @pytest.mark.parametrize("schema_uid", ["gone", None])
    def test_a_dropped_or_unknown_attribute_is_not_migrated_for_a_mapper(
        self, schemas: Schemas, schema_uid: str | None
    ):
        # Arrange
        migration = self._migration(schemas)
        uid: UUID = schemas.gone.uid if schema_uid else uuid4()
        attribute = StringAttribute(uid=uuid4(), schema_uid=uid)

        # Act & Assert
        assert migration.migrate_attribute(attribute) is None

    def test_an_attribute_schema_shared_by_item_schemas_migrated_alike_is_kept(
        self, schemas: Schemas
    ):
        """Each item schema declares the migrators of its own."""
        # Arrange
        other_source, other_target = self._other_being(schemas)

        # Act
        migration = DeclarativeSchemaMigration(
            self._root(schemas.source, other_source),
            self._root(schemas.target, other_target),
            item_migrators=[
                schemas.migrator(),
                EntityMigrator[Item](
                    other_source, other_target, **schemas.migrator_declarations()
                ),
            ],
        )

        # Assert
        migrated = migration.migrate_attribute(
            schemas.enum(schemas.colour, original_value="Navy")
        )
        assert migrated is not None
        assert migrated.schema_uid == schemas.target_colour.uid
        assert migrated.original_value == "BLUE"
        assert migration.migrate_attribute_schema(schemas.sex) == schemas.target_sex

    def test_an_attribute_schema_shared_with_another_migrator_is_refused(
        self, schemas: Schemas
    ):
        # Arrange
        other_source, other_target = self._other_being(schemas)
        declarations = schemas.migrator_declarations()
        declarations["migrated_attributes"] = [
            (schemas.sex, FixedValueAttributeMigrator("Male")),
            *declarations["migrated_attributes"][1:],
        ]

        # Act & Assert
        with pytest.raises(ValueError, match=str(schemas.sex.uid)):
            DeclarativeSchemaMigration(
                self._root(schemas.source, other_source),
                self._root(schemas.target, other_target),
                item_migrators=[
                    schemas.migrator(),
                    EntityMigrator[Item](other_source, other_target, **declarations),
                ],
            )

    def test_an_attribute_schema_shared_with_another_target_is_refused(
        self, schemas: Schemas
    ):
        # Arrange
        other_source, other_target = self._other_being(schemas)
        other_sex = schemas.target_sex.model_copy(update={"uid": uuid4()})
        other_target = other_target.model_copy(
            update={"attributes": {**other_target.attributes, "sex": other_sex}}
        )

        # Act & Assert
        with pytest.raises(ValueError, match="migrated differently") as error:
            DeclarativeSchemaMigration(
                self._root(schemas.source, other_source),
                self._root(schemas.target, other_target),
                item_migrators=[
                    schemas.migrator(),
                    EntityMigrator[Item](
                        other_source, other_target, **schemas.migrator_declarations()
                    ),
                ],
            )
        assert str(schemas.sex.uid) in str(error.value)
        assert str(other_sex.uid) in str(error.value)

    @staticmethod
    def _migration(schemas: Schemas) -> DeclarativeSchemaMigration:
        return DeclarativeSchemaMigration(
            schemas.root(schemas.source),
            schemas.root(schemas.target),
            item_migrators=[schemas.migrator()],
        )

    @staticmethod
    def _other_being(schemas: Schemas) -> tuple[SampleSchema, SampleSchema]:
        """A second item schema in each root, with the attribute schemas of the
        being."""
        uid = uuid4()
        return (
            schemas.source.model_copy(update={"uid": uid, "name": "other"}),
            schemas.target.model_copy(update={"uid": uid, "name": "other"}),
        )

    @staticmethod
    def _root(*samples: SampleSchema) -> RootSchema:
        return RootSchema(
            uid=uuid4(),
            name="root",
            project=ProjectSchema(uid=uuid4(), name="project", display_name="Project"),
            dataset=DatasetSchema(uid=uuid4(), name="dataset", display_name="Dataset"),
            samples={sample.uid: sample for sample in samples},
        )
