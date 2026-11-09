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

"""Tests for moving a value between the ends of paths on items, down into objects and
lists, see `AttributeService.move_attribute_value`."""

from typing import Any, cast
from uuid import uuid4

import pytest
from decoy import Decoy, matchers
from sqlalchemy.orm import Session

from slidetap.database import DatabaseItem
from slidetap.model import (
    AnyAttribute,
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    ListAttribute,
    ListAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    StringAttribute,
    StringAttributeSchema,
)
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
)

MELANOMA = Code(code="1162635006", scheme="SCT", meaning="Malignant melanoma")
SCAR = Code(code="12402003", scheme="SCT", meaning="Scar")
KERATOSIS = Code(code="856006", scheme="SCT", meaning="Actinic keratosis")
NEVUS = Code(code="398943008", scheme="SCT", meaning="Dysplastic nevus")


class FakeRow:
    """A top-level attribute of an item, as far as moving reads and writes it:
    its tag, its model, and the value it is set to."""

    def __init__(self, attribute: AnyAttribute, tag: str):
        self.tag = tag
        self._attribute = attribute

    @property
    def model(self) -> AnyAttribute:
        return self._attribute.model_copy(deep=True)

    def set_value(self, value: Any, display_value: str | None) -> None:
        self._attribute = self._attribute.model_copy(
            update={"updated_value": value, "display_value": display_value}
        )


class FakeItem:
    def __init__(self, *rows: FakeRow):
        self.attributes = list(rows)
        self.private_attributes: list[FakeRow] = []


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
def note_schema() -> StringAttributeSchema:
    return StringAttributeSchema(
        uid=uuid4(),
        tag="note",
        name="note",
        display_name="Note",
        optional=True,
        read_only=False,
    )


@pytest.fixture()
def statement_schema(
    list_schema: ListAttributeSchema, note_schema: StringAttributeSchema
) -> ObjectAttributeSchema:
    return ObjectAttributeSchema(
        uid=uuid4(),
        tag="statement",
        name="statement",
        display_name="Statement",
        optional=False,
        read_only=False,
        display_attributes_in_parent=False,
        display_value_tags=["diagnoses"],
        attributes={"diagnoses": list_schema, "note": note_schema},
    )


@pytest.fixture()
def schema_service(
    decoy: Decoy,
    diagnose_schema: CodeAttributeSchema,
    list_schema: ListAttributeSchema,
    note_schema: StringAttributeSchema,
    statement_schema: ObjectAttributeSchema,
) -> SchemaService:
    service = decoy.mock(cls=SchemaService)
    for schema in (diagnose_schema, list_schema, note_schema, statement_schema):
        decoy.when(service.get_any_attribute(schema.uid)).then_return(schema)
    return service


@pytest.fixture()
def attribute_service(decoy: Decoy, schema_service: SchemaService) -> AttributeService:
    return AttributeService(
        schema_service=schema_service,
        validation_service=decoy.mock(cls=ValidationService),
        database_service=decoy.mock(cls=DatabaseService),
        review_service=decoy.mock(cls=ReviewService),
    )


@pytest.fixture()
def session(decoy: Decoy) -> Session:
    return decoy.mock(cls=Session)


@pytest.fixture()
def make_item(
    diagnose_schema: CodeAttributeSchema,
    list_schema: ListAttributeSchema,
    note_schema: StringAttributeSchema,
    statement_schema: ObjectAttributeSchema,
):
    """An item with a statement holding a list of the codes, as imported."""

    def make(*codes: Code, note: str | None = None) -> FakeItem:
        held: dict[str, AnyAttribute] = {
            "diagnoses": ListAttribute(
                uid=uuid4(),
                schema_uid=list_schema.uid,
                original_value=[
                    CodeAttribute(
                        uid=uuid4(),
                        schema_uid=diagnose_schema.uid,
                        original_value=code,
                        display_value=code.meaning,
                    )
                    for code in codes
                ],
            )
        }
        if note is not None:
            held["note"] = StringAttribute(
                uid=uuid4(), schema_uid=note_schema.uid, original_value=note
            )
        statement = ObjectAttribute(
            uid=uuid4(), schema_uid=statement_schema.uid, original_value=held
        )
        return FakeItem(FakeRow(statement, "statement"))

    return make


def codes(item: FakeItem) -> list[Any]:
    """The codes of the list of the item, as it now reads."""
    statement = item.attributes[0].model
    assert isinstance(statement, ObjectAttribute)
    assert statement.value is not None
    diagnoses = statement.value["diagnoses"]
    assert isinstance(diagnoses, ListAttribute)
    return [entry.value for entry in diagnoses.value or []]


def as_item(item: FakeItem) -> DatabaseItem:
    return cast(DatabaseItem, item)


@pytest.mark.unittest
class TestMoveAttributeValue:
    def test_two_entries_of_a_list_swap_places(
        self, attribute_service: AttributeService, make_item, session: Session
    ):
        """Making one the main diagnose: putting it first."""
        # Arrange
        item = make_item(MELANOMA, SCAR, KERATOSIS)

        # Act
        attribute_service.move_attribute_value(
            as_item(item),
            ["statement", "diagnoses", 2],
            as_item(item),
            ["statement", "diagnoses", 0],
            session,
        )

        # Assert
        assert codes(item) == [KERATOSIS, SCAR, MELANOMA]

    def test_entries_swap_between_items(
        self, attribute_service: AttributeService, make_item, session: Session
    ):
        # Arrange
        source = make_item(MELANOMA, SCAR)
        target = make_item(KERATOSIS)

        # Act
        attribute_service.move_attribute_value(
            as_item(source),
            ["statement", "diagnoses", 1],
            as_item(target),
            ["statement", "diagnoses", 0],
            session,
        )

        # Assert
        assert codes(source) == [MELANOMA, KERATOSIS]
        assert codes(target) == [SCAR]

    def test_an_entry_moved_past_the_last_of_another_list_is_appended(
        self, attribute_service: AttributeService, make_item, session: Session
    ):
        # Arrange
        source = make_item(MELANOMA, SCAR)
        target = make_item(KERATOSIS)

        # Act
        attribute_service.move_attribute_value(
            as_item(source),
            ["statement", "diagnoses", 0],
            as_item(target),
            ["statement", "diagnoses", 1],
            session,
        )

        # Assert
        assert codes(source) == [SCAR]
        assert codes(target) == [KERATOSIS, MELANOMA]

    def test_an_entry_moved_past_the_last_of_its_own_list_goes_last(
        self, attribute_service: AttributeService, make_item, session: Session
    ):
        # Arrange
        item = make_item(MELANOMA, SCAR, KERATOSIS)

        # Act
        attribute_service.move_attribute_value(
            as_item(item),
            ["statement", "diagnoses", 0],
            as_item(item),
            ["statement", "diagnoses", 3],
            session,
        )

        # Assert
        assert codes(item) == [SCAR, KERATOSIS, MELANOMA]

    def test_the_last_entry_moved_out_leaves_the_list_empty(
        self, attribute_service: AttributeService, make_item, session: Session
    ):
        """Empty as edited, not back to what was imported."""
        # Arrange
        source = make_item(MELANOMA)
        target = make_item(SCAR)

        # Act
        attribute_service.move_attribute_value(
            as_item(source),
            ["statement", "diagnoses", 0],
            as_item(target),
            ["statement", "diagnoses", 1],
            session,
        )

        # Assert
        assert codes(source) == []
        assert codes(target) == [SCAR, MELANOMA]

    def test_what_was_imported_is_kept(
        self, attribute_service: AttributeService, make_item, session: Session
    ):
        # Arrange
        source = make_item(MELANOMA, SCAR)
        target = make_item(KERATOSIS)
        imported = source.attributes[0].model.original_value

        # Act
        attribute_service.move_attribute_value(
            as_item(source),
            ["statement", "diagnoses", 0],
            as_item(target),
            ["statement", "diagnoses", 0],
            session,
        )

        # Assert
        assert source.attributes[0].model.original_value == imported

    def test_the_display_values_follow(
        self, attribute_service: AttributeService, make_item, session: Session
    ):
        # Arrange
        item = make_item(MELANOMA, SCAR)

        # Act
        attribute_service.move_attribute_value(
            as_item(item),
            ["statement", "diagnoses", 1],
            as_item(item),
            ["statement", "diagnoses", 0],
            session,
        )

        # Assert
        statement = item.attributes[0].model
        assert isinstance(statement, ObjectAttribute)
        assert statement.value is not None
        for display_value in (
            statement.value["diagnoses"].display_value,
            statement.display_value,
        ):
            assert display_value is not None
            assert display_value.index("Scar") < display_value.index(
                "Malignant melanoma"
            )

    def test_values_at_paths_the_schema_service_refuses_are_not_moved(
        self,
        decoy: Decoy,
        attribute_service: AttributeService,
        schema_service: SchemaService,
        make_item,
        session: Session,
    ):
        """Paths that do not lead to the same kind, see
        `SchemaService.assert_paths_hold_same_kind`."""
        # Arrange
        source = make_item(MELANOMA, SCAR)
        target = make_item(KERATOSIS)
        decoy.when(
            schema_service.assert_paths_hold_same_kind(
                matchers.Anything(),
                matchers.Anything(),
                matchers.Anything(),
                matchers.Anything(),
            )
        ).then_raise(ValueError("Not the same kind."))

        # Act & Assert
        with pytest.raises(ValueError):
            attribute_service.move_attribute_value(
                as_item(source),
                ["statement", "diagnoses", 0],
                as_item(target),
                ["statement", "diagnoses", 0],
                session,
            )
        assert codes(source) == [MELANOMA, SCAR]
        assert codes(target) == [KERATOSIS]

    @pytest.mark.parametrize(
        ("source_path", "target_path"),
        [
            (["statement"], ["statement", "diagnoses", 0]),
            (["statement", "diagnoses", 0], ["statement"]),
        ],
    )
    def test_a_whole_attribute_and_a_value_inside_one_are_not_moved(
        self,
        attribute_service: AttributeService,
        make_item,
        session: Session,
        source_path: list[str | int],
        target_path: list[str | int],
    ):
        # Arrange
        source = make_item(MELANOMA, SCAR)
        target = make_item(KERATOSIS)

        # Act & Assert
        with pytest.raises(ValueError, match="whole attribute"):
            attribute_service.move_attribute_value(
                as_item(source), source_path, as_item(target), target_path, session
            )
        assert codes(source) == [MELANOMA, SCAR]
        assert codes(target) == [KERATOSIS]

    @pytest.mark.parametrize("position", [-1, 5])
    def test_a_position_outside_the_list_is_refused(
        self,
        attribute_service: AttributeService,
        make_item,
        session: Session,
        position: int,
    ):
        # Arrange
        source = make_item(MELANOMA)
        target = make_item(SCAR)

        # Act & Assert
        with pytest.raises(ValueError):
            attribute_service.move_attribute_value(
                as_item(source),
                ["statement", "diagnoses", 0],
                as_item(target),
                ["statement", "diagnoses", position],
                session,
            )

    def test_nothing_is_moved_from_past_the_last_of_a_list(
        self, attribute_service: AttributeService, make_item, session: Session
    ):
        # Arrange
        source = make_item(MELANOMA)
        target = make_item(SCAR)

        # Act & Assert
        with pytest.raises(ValueError):
            attribute_service.move_attribute_value(
                as_item(source),
                ["statement", "diagnoses", 1],
                as_item(target),
                ["statement", "diagnoses", 0],
                session,
            )
