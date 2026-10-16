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

"""Tests that an owner holds one attribute of each attribute schema.

An attribute row is held through one owner column and has the others null.
The database keeps the invariant per owner column, so a second attribute of
the same schema on the same owner is refused rather than silently shadowing
the first when the owner's attributes are read by tag.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from slidetap.database import DatabaseAttribute, DatabaseStringAttribute
from slidetap.services import DatabaseService


def _attribute(schema_uid: UUID, owner_column: str, owner_uid: UUID):
    attribute = DatabaseStringAttribute(
        tag="tag", schema_uid=schema_uid, original_value="value"
    )
    setattr(attribute, owner_column, owner_uid)
    return attribute


@pytest.mark.integration
class TestAttributeUniqueness:
    @pytest.mark.parametrize("owner_column", DatabaseAttribute.OWNER_COLUMNS)
    def test_an_owner_holds_one_attribute_of_a_schema(
        self, sqlite_database_service: DatabaseService, owner_column: str
    ):
        # Arrange
        schema_uid, owner_uid = uuid4(), uuid4()
        with sqlite_database_service.get_session() as session:
            session.add(_attribute(schema_uid, owner_column, owner_uid))

        # Act & Assert
        with (
            pytest.raises(IntegrityError),
            sqlite_database_service.get_session() as session,
        ):
            session.add(_attribute(schema_uid, owner_column, owner_uid))

    @pytest.mark.parametrize("owner_column", DatabaseAttribute.OWNER_COLUMNS)
    def test_owners_each_hold_an_attribute_of_a_schema(
        self, sqlite_database_service: DatabaseService, owner_column: str
    ):
        # Arrange
        schema_uid = uuid4()

        # Act
        with sqlite_database_service.get_session() as session:
            session.add(_attribute(schema_uid, owner_column, uuid4()))
            session.add(_attribute(schema_uid, owner_column, uuid4()))
            session.add(_attribute(uuid4(), owner_column, uuid4()))

        # Assert
        with sqlite_database_service.get_session() as session:
            assert session.query(DatabaseStringAttribute).count() == 3

    def test_attributes_without_an_owner_are_not_held_to_it(
        self, sqlite_database_service: DatabaseService
    ):
        # Arrange
        schema_uid = uuid4()

        # Act
        with sqlite_database_service.get_session() as session:
            for _ in range(2):
                session.add(DatabaseStringAttribute(tag="tag", schema_uid=schema_uid))

        # Assert
        with sqlite_database_service.get_session() as session:
            assert session.query(DatabaseStringAttribute).count() == 2
