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

"""Tests for how far stepping from one item to the next reaches.

A view of one item is opened from a list, and the arrows on it walk that list.
Which list that was is what the caller says: a batch when it is a batch's view,
the whole dataset when it is the project's.
"""

from uuid import UUID, uuid4

import pytest

from slidetap.model import Dataset, Project, RootSchema
from slidetap.model.batch import BatchCreate
from slidetap.model.item import Sample
from slidetap.model.schema.item_schema import SampleSchema
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ItemService,
    MapperService,
    ReviewService,
    SchemaService,
    TagService,
    ValidationService,
)


@pytest.fixture()
def sample_schema(schema: RootSchema) -> SampleSchema:
    return next(iter(schema.samples.values()))


@pytest.fixture()
def item_service(
    sqlite_database_service: DatabaseService, schema: RootSchema
) -> ItemService:
    schema_service = SchemaService(schema)
    validation_service = ValidationService(schema_service, sqlite_database_service)
    review_service = ReviewService(
        schema_service, validation_service, sqlite_database_service
    )
    attribute_service = AttributeService(
        schema_service, validation_service, sqlite_database_service, review_service
    )
    return ItemService(
        attribute_service,
        TagService(sqlite_database_service),
        MapperService(
            attribute_service,
            validation_service,
            schema_service,
            sqlite_database_service,
            review_service,
        ),
        schema_service,
        validation_service,
        sqlite_database_service,
        review_service,
    )


@pytest.fixture()
def samples(
    sqlite_database_service: DatabaseService,
    sample_schema: SampleSchema,
    dataset: Dataset,
    project: Project,
) -> dict[str, tuple[UUID, UUID]]:
    """Two samples in a first batch and one in a second, by identifier.

    Named so that the second batch's sample sorts between the first batch's
    two: stepping that reached across the batches would land on it.
    """
    added: dict[str, tuple[UUID, UUID]] = {}
    with sqlite_database_service.get_session() as session:
        sqlite_database_service.add_dataset(session, dataset)
        sqlite_database_service.add_project(session, project)
        for batch_name, identifiers in (("first", ("a", "c")), ("second", ("b",))):
            batch = sqlite_database_service.add_batch(
                session, BatchCreate(name=batch_name, project_uid=project.uid)
            )
            for identifier in identifiers:
                sample = Sample(
                    uid=uuid4(),
                    identifier=identifier,
                    pseudonym=identifier.upper(),
                    dataset_uid=dataset.uid,
                    batch_uid=batch.uid,
                    schema_uid=sample_schema.uid,
                )
                added[identifier] = (
                    sqlite_database_service.add_item(session, sample, [], []).uid,
                    batch.uid,
                )
    return added


@pytest.mark.integration
class TestItemNeighbours:
    def test_a_batch_is_stepped_through_on_its_own(
        self,
        item_service: ItemService,
        samples: dict[str, tuple[UUID, UUID]],
    ):
        # Arrange
        first_uid, first_batch_uid = samples["a"]

        # Act
        neighbours = item_service.get_neighbours(first_uid, first_batch_uid)

        # Assert
        assert neighbours.previous_uid is None
        assert neighbours.next_uid == samples["c"][0]

    def test_the_dataset_is_stepped_through_without_a_batch(
        self,
        item_service: ItemService,
        samples: dict[str, tuple[UUID, UUID]],
    ):
        # Arrange
        first_uid, _ = samples["a"]

        # Act
        neighbours = item_service.get_neighbours(first_uid)

        # Assert
        assert neighbours.previous_uid is None
        assert neighbours.next_uid == samples["b"][0]
