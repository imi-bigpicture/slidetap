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

"""Tests for lists whose entries may not say the same, see
`ListAttributeSchema.unique_items`."""

from uuid import uuid4

import pytest

from slidetap.model import (
    AnyAttribute,
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    ListAttribute,
    ListAttributeSchema,
    StringAttribute,
    StringAttributeSchema,
)
from slidetap.services.validators.attribute_validator import AttributeValidator

MELANOMA = Code(code="1162635006", scheme="SCT", meaning="Malignant melanoma")
SCAR = Code(code="12402003", scheme="SCT", meaning="Scar")


def code_entry_schema(optional: bool) -> CodeAttributeSchema:
    return CodeAttributeSchema(
        uid=uuid4(),
        tag="diagnose",
        name="diagnose",
        display_name="Diagnose",
        optional=optional,
        read_only=False,
    )


@pytest.fixture()
def code_schema() -> CodeAttributeSchema:
    return code_entry_schema(optional=False)


@pytest.fixture()
def optional_code_schema() -> CodeAttributeSchema:
    """Entries of it with no code, such as one still to be mapped, are valid
    on their own, so a list of them is valid or not by its repeats alone."""
    return code_entry_schema(optional=True)


def list_schema(
    entry: CodeAttributeSchema | StringAttributeSchema, unique_items: bool
) -> ListAttributeSchema:
    return ListAttributeSchema(
        uid=uuid4(),
        tag="diagnoses",
        name="diagnoses",
        display_name="Diagnoses",
        optional=False,
        read_only=False,
        display_attributes_in_parent=False,
        attribute=entry,
        unique_items=unique_items,
    )


def code(
    schema: CodeAttributeSchema,
    value: Code | None = None,
    mappable: str | None = None,
) -> CodeAttribute:
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=schema.uid,
        original_value=value,
        mappable_value=mappable,
    )


def validate(schema: ListAttributeSchema, *entries: AnyAttribute) -> bool:
    attribute = ListAttribute(
        uid=uuid4(), schema_uid=schema.uid, original_value=list(entries)
    )
    return AttributeValidator.validate_attribute(attribute, schema)


@pytest.mark.unittest
class TestUniqueListEntries:
    def test_different_entries_are_valid(self, code_schema: CodeAttributeSchema):
        # Arrange
        schema = list_schema(code_schema, unique_items=True)

        # Act
        valid = validate(schema, code(code_schema, MELANOMA), code(code_schema, SCAR))

        # Assert
        assert valid

    def test_the_same_code_twice_is_not_valid(self, code_schema: CodeAttributeSchema):
        # Arrange
        schema = list_schema(code_schema, unique_items=True)

        # Act
        valid = validate(
            schema,
            code(code_schema, MELANOMA),
            code(code_schema, SCAR),
            code(code_schema, MELANOMA),
        )

        # Assert
        assert not valid

    def test_a_code_is_the_same_whatever_its_meaning_reads(
        self, code_schema: CodeAttributeSchema
    ):
        """Two local codes mapped to one concept, worded otherwise."""
        # Arrange
        schema = list_schema(code_schema, unique_items=True)
        reworded = MELANOMA.model_copy(update={"meaning": "Melanoma, malignant"})

        # Act
        valid = validate(
            schema, code(code_schema, MELANOMA), code(code_schema, reworded)
        )

        # Assert
        assert not valid

    def test_the_same_text_to_map_by_twice_is_not_valid(
        self, optional_code_schema: CodeAttributeSchema
    ):
        # Arrange
        schema = list_schema(optional_code_schema, unique_items=True)

        # Act
        valid = validate(
            schema,
            code(optional_code_schema, mappable="M80702"),
            code(optional_code_schema, mappable=" M80702 "),
        )

        # Assert
        assert not valid

    def test_text_to_map_by_is_not_compared_with_a_code(
        self, optional_code_schema: CodeAttributeSchema
    ):
        # Arrange
        schema = list_schema(optional_code_schema, unique_items=True)

        # Act
        valid = validate(
            schema,
            code(optional_code_schema, MELANOMA),
            code(optional_code_schema, mappable="M87203"),
        )

        # Assert
        assert valid

    def test_entries_saying_nothing_are_not_compared(
        self, optional_code_schema: CodeAttributeSchema
    ):
        # Arrange
        schema = list_schema(optional_code_schema, unique_items=True)

        # Act
        valid = validate(
            schema,
            code(optional_code_schema),
            code(optional_code_schema),
            code(optional_code_schema, MELANOMA),
        )

        # Assert
        assert valid

    def test_text_is_compared_trimmed(self):
        # Arrange
        text_schema = StringAttributeSchema(
            uid=uuid4(),
            tag="note",
            name="note",
            display_name="Note",
            optional=False,
            read_only=False,
        )
        schema = list_schema(text_schema, unique_items=True)
        entries = [
            StringAttribute(uid=uuid4(), schema_uid=text_schema.uid, original_value=v)
            for v in ("Seen before", " Seen before ")
        ]

        # Act
        valid = validate(schema, *entries)

        # Assert
        assert not valid

    def test_a_list_not_asking_for_it_may_repeat(
        self, code_schema: CodeAttributeSchema
    ):
        # Arrange
        schema = list_schema(code_schema, unique_items=False)

        # Act
        valid = validate(
            schema, code(code_schema, MELANOMA), code(code_schema, MELANOMA)
        )

        # Assert
        assert valid
