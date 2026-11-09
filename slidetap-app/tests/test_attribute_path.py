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

"""Tests for `AttributePath`, a path down inside an attribute."""

from uuid import uuid4

import pytest

from slidetap.model import (
    AttributePath,
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    ListAttribute,
    ListAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
)

MELANOMA = Code(code="1162635006", scheme="SCT", meaning="Malignant melanoma")
SCAR = Code(code="12402003", scheme="SCT", meaning="Scar")
KERATOSIS = Code(code="856006", scheme="SCT", meaning="Actinic keratosis")


@pytest.fixture()
def diagnose_schema() -> CodeAttributeSchema:
    return CodeAttributeSchema(
        uid=uuid4(),
        tag="diagnose",
        name="diagnose",
        display_name="Diagnose",
        optional=False,
        read_only=False,
    )


@pytest.fixture()
def list_schema(diagnose_schema: CodeAttributeSchema) -> ListAttributeSchema:
    return ListAttributeSchema(
        uid=uuid4(),
        tag="diagnoses",
        name="diagnoses",
        display_name="Diagnoses",
        optional=False,
        read_only=False,
        display_attributes_in_parent=False,
        attribute=diagnose_schema,
    )


@pytest.fixture()
def statement_schema(list_schema: ListAttributeSchema) -> ObjectAttributeSchema:
    return ObjectAttributeSchema(
        uid=uuid4(),
        tag="statement",
        name="statement",
        display_name="Statement",
        optional=False,
        read_only=False,
        display_attributes_in_parent=False,
        display_value_tags=["diagnoses"],
        attributes={"diagnoses": list_schema},
    )


@pytest.fixture()
def statement(
    diagnose_schema: CodeAttributeSchema,
    list_schema: ListAttributeSchema,
    statement_schema: ObjectAttributeSchema,
) -> ObjectAttribute:
    """A statement as imported, with melanoma and scar in its list."""
    diagnoses = ListAttribute(
        uid=uuid4(),
        schema_uid=list_schema.uid,
        original_value=[
            CodeAttribute(
                uid=uuid4(),
                schema_uid=diagnose_schema.uid,
                original_value=code,
                display_value=code.meaning,
            )
            for code in (MELANOMA, SCAR)
        ],
    )
    return ObjectAttribute(
        uid=uuid4(),
        schema_uid=statement_schema.uid,
        original_value={"diagnoses": diagnoses},
    )


def attribute_path(*steps: str | int) -> AttributePath:
    return AttributePath(steps=steps)


def codes(statement: ObjectAttribute) -> list[object]:
    assert statement.value is not None
    diagnoses = statement.value["diagnoses"]
    assert isinstance(diagnoses, ListAttribute)
    return [entry.value for entry in diagnoses.value or []]


@pytest.mark.unittest
class TestAttributePath:
    def test_the_parent_is_the_path_to_what_holds_its_end(self):
        # Act
        parent = attribute_path("diagnoses", 2).parent

        # Assert
        assert parent == attribute_path("diagnoses")

    def test_the_attribute_itself_has_no_parent(self):
        # Act & Assert
        with pytest.raises(ValueError):
            _ = attribute_path().parent

    def test_a_path_on_an_item_gives_the_tag_and_the_path_inside(self):
        # Act
        tag, path = AttributePath.from_item_path(["statement", "diagnoses", 2])

        # Assert
        assert tag == "statement"
        assert path == attribute_path("diagnoses", 2)

    @pytest.mark.parametrize("path", [[], [0, "diagnoses"]])
    def test_a_path_not_starting_with_a_tag_is_refused(self, path: list[str | int]):
        # Act & Assert
        with pytest.raises(ValueError):
            AttributePath.from_item_path(path)

    @pytest.mark.parametrize(
        ("first", "second", "overlap"),
        [
            (attribute_path("diagnoses", 1), attribute_path("diagnoses"), True),
            (attribute_path("diagnoses"), attribute_path("diagnoses", 1), True),
            (attribute_path("diagnoses"), attribute_path("diagnoses"), False),
            (attribute_path("diagnoses", 0), attribute_path("diagnoses", 1), False),
            (attribute_path("note"), attribute_path("diagnoses"), False),
        ],
    )
    def test_paths_overlap_only_when_one_goes_on_from_the_other(
        self, first: AttributePath, second: AttributePath, overlap: bool
    ):
        # Act
        result = first.overlaps(second)

        # Assert
        assert result is overlap

    @pytest.mark.parametrize(
        ("path", "removed", "expected"),
        [
            # A later entry of the same list moves up.
            (
                attribute_path("diagnoses", 3),
                attribute_path("diagnoses", 1),
                attribute_path("diagnoses", 2),
            ),
            # An earlier one does not.
            (
                attribute_path("diagnoses", 0),
                attribute_path("diagnoses", 1),
                attribute_path("diagnoses", 0),
            ),
            # Nor does a path through another list.
            (
                attribute_path("others", 3),
                attribute_path("diagnoses", 1),
                attribute_path("others", 3),
            ),
        ],
    )
    def test_a_path_after_removal_of_an_entry(
        self, path: AttributePath, removed: AttributePath, expected: AttributePath
    ):
        # Act
        adjusted = path.after_removal_of(removed)

        # Assert
        assert adjusted == expected

    def test_the_schema_is_found_through_objects_and_lists(
        self,
        statement_schema: ObjectAttributeSchema,
        diagnose_schema: CodeAttributeSchema,
    ):
        # Act
        schema = attribute_path("diagnoses", 0).schema_in(statement_schema)

        # Assert
        assert schema == diagnose_schema

    @pytest.mark.parametrize(
        "path",
        [attribute_path("note"), attribute_path(0), attribute_path("diagnoses", "x")],
    )
    def test_a_step_that_does_not_go_down_is_refused(
        self, statement_schema: ObjectAttributeSchema, path: AttributePath
    ):
        # Act & Assert
        with pytest.raises(ValueError):
            path.schema_in(statement_schema)

    def test_the_value_held_is_read(self, statement: ObjectAttribute):
        # Act
        held = attribute_path("diagnoses", 1).value_in(statement)

        # Assert
        assert held is not None
        assert held.value == SCAR

    def test_nothing_is_held_past_the_last_of_a_list(self, statement: ObjectAttribute):
        # Act
        held = attribute_path("diagnoses", 2).value_in(statement)

        # Assert
        assert held is None

    def test_a_position_outside_a_list_is_refused(self, statement: ObjectAttribute):
        # Act & Assert
        with pytest.raises(ValueError):
            attribute_path("diagnoses", 3).value_in(statement)

    def test_a_value_is_appended_past_the_last_of_a_list(
        self,
        statement: ObjectAttribute,
        statement_schema: ObjectAttributeSchema,
        diagnose_schema: CodeAttributeSchema,
    ):
        # Arrange
        keratosis = CodeAttribute(
            uid=uuid4(), schema_uid=diagnose_schema.uid, original_value=KERATOSIS
        )

        # Act
        changed = attribute_path("diagnoses", 2).replaced_in(
            statement, statement_schema, keratosis
        )

        # Assert
        assert isinstance(changed, ObjectAttribute)
        assert codes(changed) == [MELANOMA, SCAR, KERATOSIS]

    def test_an_entry_taken_out_closes_the_gap(
        self, statement: ObjectAttribute, statement_schema: ObjectAttributeSchema
    ):
        # Act
        changed = attribute_path("diagnoses", 0).replaced_in(
            statement, statement_schema, None
        )

        # Assert
        assert isinstance(changed, ObjectAttribute)
        assert codes(changed) == [SCAR]

    def test_a_replacement_is_an_edit_keeping_what_was_imported(
        self, statement: ObjectAttribute, statement_schema: ObjectAttributeSchema
    ):
        # Act
        changed = attribute_path("diagnoses", 0).replaced_in(
            statement, statement_schema, None
        )

        # Assert
        assert changed.original_value == statement.original_value
        assert changed.updated_value is not None
        assert codes(statement) == [MELANOMA, SCAR]

    def test_the_display_values_on_the_way_are_made_again(
        self, statement: ObjectAttribute, statement_schema: ObjectAttributeSchema
    ):
        # Act
        changed = attribute_path("diagnoses", 0).replaced_in(
            statement, statement_schema, None
        )

        # Assert
        assert isinstance(changed, ObjectAttribute)
        assert changed.value is not None
        for display_value in (
            changed.display_value,
            changed.value["diagnoses"].display_value,
        ):
            assert display_value is not None
            assert "Scar" in display_value
            assert "Malignant melanoma" not in display_value
