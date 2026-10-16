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

import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from slidetap.database import (
    DatabaseAttribute,
    DatabaseBatch,
    DatabaseDataset,
    DatabaseProject,
    DatabaseSample,
    DatabaseStringAttribute,
)
from slidetap.services import DatabaseService


def _attribute(schema_uid: UUID, owner_column: str, owner_uid: UUID):
    attribute = DatabaseStringAttribute(
        tag="tag", schema_uid=schema_uid, original_value="value"
    )
    setattr(attribute, owner_column, owner_uid)
    return attribute


def _add_owner(database_service: DatabaseService, owner_column: str) -> UUID:
    """Store a dataset, a project and an item in it, and return the uid of the
    one the owner column points at."""
    with database_service.get_session() as session:
        dataset = DatabaseDataset("dataset", uuid4())
        session.add(dataset)
        project = DatabaseProject(
            "project", uuid4(), uuid4(), dataset.uid, datetime.datetime(2026, 10, 16)
        )
        session.add(project)
        batch = DatabaseBatch("batch", project.uid, datetime.datetime(2026, 10, 16))
        session.add(batch)
        item = DatabaseSample(dataset.uid, batch.uid, uuid4(), "sample")
        session.add(item)
        session.commit()
        owners = {
            "item_uid": item.uid,
            "project_uid": project.uid,
            "dataset_uid": dataset.uid,
        }
        return owners[owner_column.removeprefix("private_").removeprefix("attribute_")]


@pytest.mark.integration
class TestAttributeUniqueness:
    @pytest.mark.parametrize("owner_column", DatabaseAttribute.OWNER_COLUMNS)
    def test_an_owner_holds_one_attribute_of_a_schema(
        self, stored_database_service: DatabaseService, owner_column: str
    ):
        # Arrange
        schema_uid = uuid4()
        owner_uid = _add_owner(stored_database_service, owner_column)
        with stored_database_service.get_session() as session:
            session.add(_attribute(schema_uid, owner_column, owner_uid))

        # Act & Assert
        with (
            pytest.raises(IntegrityError),
            stored_database_service.get_session() as session,
        ):
            session.add(_attribute(schema_uid, owner_column, owner_uid))

    @pytest.mark.parametrize("owner_column", DatabaseAttribute.OWNER_COLUMNS)
    def test_owners_each_hold_an_attribute_of_a_schema(
        self, stored_database_service: DatabaseService, owner_column: str
    ):
        # Arrange
        schema_uid = uuid4()
        first_owner_uid, second_owner_uid, third_owner_uid = (
            _add_owner(stored_database_service, owner_column) for _ in range(3)
        )

        # Act
        with stored_database_service.get_session() as session:
            session.add(_attribute(schema_uid, owner_column, first_owner_uid))
            session.add(_attribute(schema_uid, owner_column, second_owner_uid))
            session.add(_attribute(uuid4(), owner_column, third_owner_uid))

        # Assert
        with stored_database_service.get_session() as session:
            assert session.query(DatabaseStringAttribute).count() == 3

    def test_attributes_without_an_owner_are_not_held_to_it(
        self, stored_database_service: DatabaseService
    ):
        # Arrange
        schema_uid = uuid4()

        # Act
        with stored_database_service.get_session() as session:
            for _ in range(2):
                session.add(DatabaseStringAttribute(tag="tag", schema_uid=schema_uid))

        # Assert
        with stored_database_service.get_session() as session:
            assert session.query(DatabaseStringAttribute).count() == 2
