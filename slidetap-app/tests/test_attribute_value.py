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

"""Tests which of the values an attribute holds is the one it has.

What was edited, else what was mapped, else what was imported — and a curator
can refuse either of the last two, which says the value is wrong where an empty
edit would only say that nobody has typed anything.
"""

from uuid import uuid4

import pytest

from slidetap.model import RejectedValues, StringAttribute


@pytest.fixture
def attribute() -> StringAttribute:
    """As imported and mapped: the report said one thing, a mapper another."""
    return StringAttribute(
        uid=uuid4(),
        schema_uid=uuid4(),
        original_value="from the report",
        mappable_value="from the report",
        mapped_value="from the mapper",
    )


class TestAttributeValue:
    def test_the_mapped_value_is_used_when_nothing_is_refused(
        self, attribute: StringAttribute
    ):
        # Arrange

        # Act
        value = attribute.value

        # Assert
        assert value == "from the mapper"

    def test_an_edit_wins_over_everything(self, attribute: StringAttribute):
        # Arrange
        edited = attribute.model_copy(
            update={
                "updated_value": "typed by a curator",
                "rejected": RejectedValues.ORIGINAL | RejectedValues.MAPPABLE,
            }
        )

        # Act
        value = edited.value

        # Assert
        assert value == "typed by a curator"

    def test_refusing_the_mappable_falls_back_to_what_was_imported(
        self, attribute: StringAttribute
    ):
        # Arrange: the mapping is wrong, the report was right.
        refused = attribute.model_copy(update={"rejected": RejectedValues.MAPPABLE})

        # Act
        value = refused.value

        # Assert
        assert value == "from the report"

    def test_refusing_the_original_leaves_what_was_mapped(
        self, attribute: StringAttribute
    ):
        # Arrange: the report is wrong, the mapping corrected it.
        refused = attribute.model_copy(update={"rejected": RejectedValues.ORIGINAL})

        # Act
        value = refused.value

        # Assert
        assert value == "from the mapper"

    def test_refusing_both_leaves_nothing(self, attribute: StringAttribute):
        # Arrange: wrong, and there is no better.
        refused = attribute.model_copy(
            update={"rejected": RejectedValues.ORIGINAL | RejectedValues.MAPPABLE}
        )

        # Act
        value = refused.value

        # Assert
        assert value is None

    def test_what_was_refused_is_kept(self, attribute: StringAttribute):
        # Arrange: judging the mapper later needs what it said.
        refused = attribute.model_copy(
            update={"rejected": RejectedValues.ORIGINAL | RejectedValues.MAPPABLE}
        )

        # Act

        # Assert
        assert refused.mapped_value == "from the mapper"
        assert refused.original_value == "from the report"
