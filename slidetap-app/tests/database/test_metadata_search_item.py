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

"""Tests that the message of a search item fits its column.

Postgres refuses a value longer than the column, so recording a failure whose
text is longer, as the text of a database error often is, would fail too.
"""

from uuid import uuid4

import pytest

from slidetap.database import DatabaseMetadataSearchItem


@pytest.mark.unittest
class TestMetadataSearchItemMessage:
    def test_a_message_that_fits_is_kept(self):
        # Arrange
        message = "Not found"

        # Act
        fitted = DatabaseMetadataSearchItem.fitted_message(message)

        # Assert
        assert fitted == message

    def test_no_message_is_kept(self):
        # Act
        fitted = DatabaseMetadataSearchItem.fitted_message(None)

        # Assert
        assert fitted is None

    def test_a_message_too_long_is_cut_to_the_column_and_marked(self):
        # Arrange
        message = "cause " + "x" * DatabaseMetadataSearchItem.MESSAGE_LENGTH

        # Act
        fitted = DatabaseMetadataSearchItem.fitted_message(message)

        # Assert
        assert fitted is not None
        assert len(fitted) == DatabaseMetadataSearchItem.MESSAGE_LENGTH
        assert fitted.startswith("cause ")
        assert fitted.endswith(DatabaseMetadataSearchItem.TRUNCATION_MARKER)

    def test_a_message_too_long_is_cut_when_the_item_is_made(self):
        # Arrange
        message = "x" * (DatabaseMetadataSearchItem.MESSAGE_LENGTH + 1)

        # Act
        item = DatabaseMetadataSearchItem(
            batch_uid=uuid4(),
            identifier="patient-1",
            schema_uid=uuid4(),
            message=message,
        )

        # Assert
        assert item.message is not None
        assert len(item.message) == DatabaseMetadataSearchItem.MESSAGE_LENGTH
