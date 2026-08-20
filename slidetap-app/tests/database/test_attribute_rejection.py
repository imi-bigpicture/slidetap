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

"""What a curator refuses is kept, but is not the value of the attribute.

`DatabaseAttribute.value` is what validation and the exporters read, so it has
to answer the same as `Attribute.value` does for the model.
"""

from uuid import uuid4

import pytest

from slidetap.database import DatabaseStringAttribute
from slidetap.model import RejectedValues


@pytest.fixture()
def attribute() -> DatabaseStringAttribute:
    return DatabaseStringAttribute(
        tag="tag",
        schema_uid=uuid4(),
        original_value="imported",
        mapped_value="mapped",
        mappable_value="raw",
    )


@pytest.mark.unittest
class TestDatabaseAttributeRejection:
    def test_nothing_refused_leaves_the_mapped_value(
        self, attribute: DatabaseStringAttribute
    ):
        # Arrange, act, assert
        # The column default is only written on insert, so this is also the
        # case of an attribute that has not been saved yet.
        assert attribute.rejected is None
        assert attribute.value == "mapped"

    def test_refusing_the_raw_value_falls_back_to_the_imported_one(
        self, attribute: DatabaseStringAttribute
    ):
        # Act
        attribute.set_rejected(RejectedValues.MAPPABLE)

        # Assert
        assert attribute.value == "imported"
        assert attribute.mapped_value == "mapped"

    def test_refusing_the_imported_value_leaves_the_mapped_one(
        self, attribute: DatabaseStringAttribute
    ):
        # Act
        attribute.set_rejected(RejectedValues.ORIGINAL)

        # Assert
        assert attribute.value == "mapped"

    def test_refusing_both_leaves_no_value(self, attribute: DatabaseStringAttribute):
        # Act
        attribute.set_rejected(RejectedValues.ORIGINAL | RejectedValues.MAPPABLE)

        # Assert
        assert attribute.value is None
        assert attribute.original_value == "imported"
        assert attribute.mapped_value == "mapped"

    def test_an_edit_wins_over_what_is_refused(
        self, attribute: DatabaseStringAttribute
    ):
        # Arrange
        attribute.set_rejected(RejectedValues.ORIGINAL | RejectedValues.MAPPABLE)

        # Act
        attribute.set_value("edited", "edited")

        # Assert
        assert attribute.value == "edited"

    def test_what_is_refused_is_carried_to_the_model(
        self, attribute: DatabaseStringAttribute
    ):
        # Act
        attribute.set_rejected(RejectedValues.MAPPABLE)

        # Assert
        assert attribute.model.rejected == RejectedValues.MAPPABLE
        assert attribute.model.value == "imported"
