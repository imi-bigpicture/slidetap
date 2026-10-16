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

"""Tests that an attribute given for a schema the owner already holds one of
replaces it.

The client sends an attribute it has just made under the nil uid, and an
importer may hand over one under a uid of its own. Either is new to the
database, while the owner holds one attribute of each schema. It is written
over the attribute the owner holds, keeping that row and its uid, rather than
inserted beside it, which the database refuses.
"""

import datetime
from typing import NamedTuple
from uuid import UUID, uuid4

import pytest
from decoy import Decoy

from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseProject,
    DatabaseSample,
    DatabaseStringAttribute,
)
from slidetap.model import RejectedValues, StringAttribute, StringAttributeSchema
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
)

NIL_UID = UUID(int=0)


@pytest.fixture()
def attribute_schema() -> StringAttributeSchema:
    return StringAttributeSchema(
        uid=uuid4(),
        tag="submitter",
        name="submitter",
        display_name="Submitter",
        optional=False,
        read_only=False,
    )


@pytest.fixture()
def attribute_service(
    decoy: Decoy,
    stored_database_service: DatabaseService,
    attribute_schema: StringAttributeSchema,
) -> AttributeService:
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.get_any_attribute(attribute_schema.uid)).then_return(
        attribute_schema
    )
    decoy.when(schema_service.get_attribute(attribute_schema.uid)).then_return(
        attribute_schema
    )
    return AttributeService(
        schema_service=schema_service,
        validation_service=decoy.mock(cls=ValidationService),
        database_service=stored_database_service,
        review_service=decoy.mock(cls=ReviewService),
    )


class StoredProject(NamedTuple):
    dataset_uid: UUID
    project_uid: UUID
    batch_uid: UUID


def _add_project(database_service: DatabaseService) -> StoredProject:
    """Store a project with its dataset and a batch, for attributes and items
    to be held under."""
    with database_service.get_session() as session:
        dataset = DatabaseDataset("dataset", uuid4())
        session.add(dataset)
        project = DatabaseProject(
            "project", uuid4(), uuid4(), dataset.uid, datetime.datetime(2026, 10, 16)
        )
        session.add(project)
        batch = DatabaseBatch("batch", project.uid, datetime.datetime(2026, 10, 16))
        session.add(batch)
        session.commit()
        return StoredProject(dataset.uid, project.uid, batch.uid)


def _held_attribute(
    database_service: DatabaseService,
    attribute_schema: StringAttributeSchema,
    owner_column: str,
    owner_uid: UUID,
) -> UUID:
    """Store the attribute the owner holds, with a value it was imported with
    and a refusal, both of which a replacement does not keep."""
    with database_service.get_session() as session:
        attribute = DatabaseStringAttribute(
            tag=attribute_schema.tag,
            schema_uid=attribute_schema.uid,
            original_value="imported",
            mappable_value="raw",
        )
        attribute.rejected = RejectedValues.MAPPABLE
        setattr(attribute, owner_column, owner_uid)
        session.add(attribute)
        session.commit()
        return attribute.uid


def _replacement(attribute_schema: StringAttributeSchema) -> StringAttribute:
    return StringAttribute(
        uid=NIL_UID, schema_uid=attribute_schema.uid, updated_value="edited"
    )


def _stored(
    database_service: DatabaseService, owner_column: str, owner_uid: UUID
) -> list[tuple[UUID, str | None, str | None, str | None, RejectedValues]]:
    with database_service.get_session() as session:
        return [
            (
                attribute.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mappable_value,
                attribute.rejected,
            )
            for attribute in session.query(DatabaseStringAttribute).filter(
                getattr(DatabaseStringAttribute, owner_column) == owner_uid
            )
        ]


@pytest.mark.integration
class TestAttributeReplacement:
    def test_a_new_attribute_for_a_held_schema_is_written_over_the_held_one(
        self,
        stored_database_service: DatabaseService,
        attribute_service: AttributeService,
        attribute_schema: StringAttributeSchema,
    ):
        """What saving a project or dataset does: its attributes are stored
        and then set as what it holds."""
        # Arrange
        project_uid = _add_project(stored_database_service).project_uid
        held_uid = _held_attribute(
            stored_database_service,
            attribute_schema,
            "attribute_project_uid",
            project_uid,
        )

        # Act
        with stored_database_service.get_session() as session:
            held = session.query(DatabaseStringAttribute).all()
            stored = attribute_service.create_or_update_attributes(
                [_replacement(attribute_schema)], session=session, held=held
            )
            stored_uids = [attribute.uid for attribute in stored]
            stored_value = stored[0].model.value

        # Assert
        assert stored_uids == [held_uid]
        assert stored_value == "edited"
        assert _stored(
            stored_database_service, "attribute_project_uid", project_uid
        ) == [(held_uid, None, "edited", None, RejectedValues.NONE)]

    def test_a_new_attribute_for_a_schema_not_held_is_added(
        self,
        stored_database_service: DatabaseService,
        attribute_service: AttributeService,
        attribute_schema: StringAttributeSchema,
    ):
        # Act
        with stored_database_service.get_session() as session:
            stored = attribute_service.create_or_update_attributes(
                [_replacement(attribute_schema)], session=session, held=[]
            )
            stored_uid = stored[0].uid

        # Assert
        assert stored_uid != NIL_UID

    def test_a_new_attribute_saved_on_an_item_is_written_over_the_held_one(
        self,
        stored_database_service: DatabaseService,
        attribute_service: AttributeService,
        attribute_schema: StringAttributeSchema,
    ):
        """What saving an item, and reading an image's own metadata into it,
        do."""
        # Arrange
        stored_project = _add_project(stored_database_service)
        with stored_database_service.get_session() as session:
            sample = DatabaseSample(
                dataset_uid=stored_project.dataset_uid,
                batch_uid=stored_project.batch_uid,
                schema_uid=uuid4(),
                identifier="PL1234-20",
            )
            session.add(sample)
            session.commit()
            sample_uid = sample.uid
        held_uid = _held_attribute(
            stored_database_service,
            attribute_schema,
            "attribute_item_uid",
            sample_uid,
        )

        # Act
        attribute_service.update_for_item(sample_uid, [_replacement(attribute_schema)])

        # Assert
        assert _stored(stored_database_service, "attribute_item_uid", sample_uid) == [
            (held_uid, None, "edited", None, RejectedValues.NONE)
        ]
