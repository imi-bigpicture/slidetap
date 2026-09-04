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

"""A nested attribute added by a client arrives without a uid of its own.

An attribute hanging off an item is a row and takes its uid from the insert.
The ones nested inside it are JSON in that row and pass no constructor, so a
client adding one has nothing to give it and says the nil uid instead. Two of
them in one list would then be one attribute twice over, since that is what
tells a nested attribute from its siblings.
"""

from uuid import UUID, uuid4

import pytest

from slidetap.database import (
    DatabaseListAttribute,
    DatabaseObjectAttribute,
    DatabaseStringAttribute,
)
from slidetap.model import ObjectAttribute, StringAttribute

NIL_UID = UUID(int=0)


def _typed(value: str) -> StringAttribute:
    """A string attribute as a client sends one it has just made."""
    return StringAttribute(uid=NIL_UID, schema_uid=uuid4(), updated_value=value)


@pytest.mark.unittest
class TestNestedAttributeUids:
    def test_children_added_to_a_list_are_told_apart(self):
        # Arrange
        keywords = [_typed("pathology"), _typed("cytology")]

        # Act
        attribute = DatabaseListAttribute(
            tag="keywords", schema_uid=uuid4(), updated_value=keywords
        )

        # Assert
        assert attribute.updated_value is not None
        uids = [child.uid for child in attribute.updated_value]
        assert NIL_UID not in uids
        assert len(set(uids)) == 2, "two children, and so two uids"

    def test_a_child_written_later_is_given_one_too(self):
        # Arrange
        attribute = DatabaseListAttribute(tag="keywords", schema_uid=uuid4())

        # Act
        attribute.set_value([_typed("pathology")], "pathology")

        # Assert
        assert attribute.updated_value is not None
        assert attribute.updated_value[0].uid != NIL_UID

    def test_a_child_that_has_a_uid_keeps_it(self):
        # Arrange
        # What a nested attribute read back and written again looks like: an
        # edit to it is found by this uid, and so is what is recorded about it.
        known = uuid4()
        child = StringAttribute(
            uid=known, schema_uid=uuid4(), updated_value="pathology"
        )

        # Act
        attribute = DatabaseListAttribute(
            tag="keywords", schema_uid=uuid4(), updated_value=[child]
        )

        # Assert
        assert attribute.updated_value is not None
        assert attribute.updated_value[0].uid == known

    def test_children_nested_deeper_are_reached(self):
        # Arrange
        # A list inside an object: only the outermost attribute is a row, and
        # everything under it is written in the same JSON.
        held = ObjectAttribute(
            uid=NIL_UID,
            schema_uid=uuid4(),
            updated_value={"keyword": _typed("pathology")},
        )

        # Act
        attribute = DatabaseObjectAttribute(
            tag="landing_page", schema_uid=uuid4(), updated_value={"held": held}
        )

        # Assert
        assert attribute.updated_value is not None
        outer = attribute.updated_value["held"]
        assert outer.uid != NIL_UID
        assert isinstance(outer, ObjectAttribute)
        assert outer.updated_value is not None
        assert outer.updated_value["keyword"].uid != NIL_UID

    def test_a_value_that_is_not_an_attribute_is_left_alone(self):
        # Arrange, act
        attribute = DatabaseStringAttribute(
            tag="tag", schema_uid=uuid4(), updated_value="pathology"
        )

        # Assert
        assert attribute.updated_value == "pathology"
