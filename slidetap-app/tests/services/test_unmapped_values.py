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

"""Tests for what counts as a value waiting for a mapping.

Covers `DatabaseService.unmapped_under`: the rule that decides what is written
to `unmapped_value`, and what `slidetap-db unmapped-values` checks that table
against. Exercised directly rather than through `record_unmapped_values`, since
it is a question about an attribute and needs no database to ask.
"""

from uuid import uuid4

import pytest

from slidetap.model import (
    Code,
    CodeAttribute,
    ListAttribute,
    ObjectAttribute,
    RejectedValues,
    StringAttribute,
)
from slidetap.services.database_service import DatabaseService


@pytest.fixture()
def mappable_value() -> str:
    """The wording the laboratory recorded. Tests needing another parametrize."""
    return "Hudstans"


@pytest.fixture()
def rejected() -> RejectedValues:
    """What the curator has refused, if anything."""
    return RejectedValues.NONE


@pytest.fixture()
def waiting(mappable_value: str, rejected: RejectedValues) -> CodeAttribute:
    """An attribute carrying a value that no mapping has resolved."""
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=uuid4(),
        mappable_value=mappable_value,
        rejected=rejected,
    )


class TestWhatCountsAsUnmapped:
    def test_a_value_with_no_mapping_is_waiting(self, waiting: CodeAttribute):
        # Arrange

        # Act
        unmapped = list(DatabaseService.unmapped_under(waiting))

        # Assert
        assert unmapped == [(waiting.uid, waiting.schema_uid, "Hudstans")]

    def test_a_mapped_value_is_not(self, waiting: CodeAttribute):
        # Arrange
        mapped = waiting.model_copy(
            update={
                "mapping_item_uid": uuid4(),
                "mapped_value": Code(
                    code="87697008", scheme="SCT", meaning="Punch biopsy"
                ),
            }
        )

        # Act
        unmapped = list(DatabaseService.unmapped_under(mapped))

        # Assert
        assert unmapped == []

    @pytest.mark.parametrize("rejected", [RejectedValues.MAPPABLE])
    def test_a_value_the_curator_refused_is_not(self, waiting: CodeAttribute):
        """Refusing the mappable value takes it out of mapping altogether, so it
        is not waiting for a key that nobody should add."""
        # Arrange

        # Act
        unmapped = list(DatabaseService.unmapped_under(waiting))

        # Assert
        assert unmapped == []

    def test_an_attribute_with_nothing_recorded_is_not(self, waiting: CodeAttribute):
        # Arrange
        empty = waiting.model_copy(update={"mappable_value": None})

        # Act
        unmapped = list(DatabaseService.unmapped_under(empty))

        # Assert
        assert unmapped == []


class TestNestedValues:
    @pytest.mark.parametrize("mappable_value", ["Skrap"])
    def test_a_value_inside_an_object_is_found(self, waiting: CodeAttribute):
        """The reason the table exists: only the outer attribute is a row, and
        this one is JSON inside it."""
        # Arrange
        outer = ObjectAttribute(
            uid=uuid4(),
            schema_uid=uuid4(),
            original_value={"preparation_type": waiting},
        )

        # Act
        unmapped = list(DatabaseService.unmapped_under(outer))

        # Assert
        assert unmapped == [(waiting.uid, waiting.schema_uid, "Skrap")]

    @pytest.mark.parametrize("mappable_value", ["Skrap"])
    def test_values_inside_a_list_are_found_separately(
        self, waiting: CodeAttribute, mappable_value: str
    ):
        """Two of the same wording are two attributes, so two rows, and the
        count of items carrying it comes out right."""
        # Arrange
        second = waiting.model_copy(update={"uid": uuid4()})
        listed = ListAttribute(
            uid=uuid4(), schema_uid=uuid4(), original_value=[waiting, second]
        )

        # Act
        unmapped = list(DatabaseService.unmapped_under(listed))

        # Assert
        assert {uid for uid, _, _ in unmapped} == {waiting.uid, second.uid}

    @pytest.mark.parametrize("mappable_value", ["Curetter"])
    def test_a_value_nested_deeply_is_found(self, waiting: CodeAttribute):
        # Arrange
        outer = ObjectAttribute(
            uid=uuid4(),
            schema_uid=uuid4(),
            original_value={
                "statement": ObjectAttribute(
                    uid=uuid4(),
                    schema_uid=uuid4(),
                    original_value={"method": waiting},
                )
            },
        )

        # Act
        unmapped = list(DatabaseService.unmapped_under(outer))

        # Assert
        assert unmapped == [(waiting.uid, waiting.schema_uid, "Curetter")]

    def test_what_is_edited_is_read_rather_than_what_was_imported(
        self, waiting: CodeAttribute
    ):
        # Arrange
        edited = waiting.model_copy(
            update={"uid": uuid4(), "mappable_value": "Hudskrap"}
        )
        outer = ObjectAttribute(
            uid=uuid4(),
            schema_uid=uuid4(),
            original_value={"method": waiting},
            updated_value={"method": edited},
        )

        # Act
        unmapped = list(DatabaseService.unmapped_under(outer))

        # Assert
        assert unmapped == [(edited.uid, edited.schema_uid, "Hudskrap")]

    def test_an_object_that_carries_a_value_itself_is_not_descended_into(
        self, waiting: CodeAttribute
    ):
        """Mapping resolves such an attribute as a whole and leaves what is
        under it alone, so nothing under it is waiting for a key of its own."""
        # Arrange
        outer = ObjectAttribute(
            uid=uuid4(),
            schema_uid=uuid4(),
            original_value={"method": waiting},
            mappable_value="Hudskrap (skalp)",
        )

        # Act
        unmapped = list(DatabaseService.unmapped_under(outer))

        # Assert
        assert unmapped == [(outer.uid, outer.schema_uid, "Hudskrap (skalp)")]

    def test_a_string_attribute_holds_no_children(self):
        # Arrange
        attribute = StringAttribute(
            uid=uuid4(), schema_uid=uuid4(), original_value="free text"
        )

        # Act
        unmapped = list(DatabaseService.unmapped_under(attribute))

        # Assert
        assert unmapped == []
