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

"""Tests that a table limited to some items, such as those of a group, gets
them however many they are.

A group, or the items in no group, can be tens of thousands, more than a
statement takes as parameters, so the uids cannot each be one.
"""

from uuid import UUID, uuid4

import pytest

from slidetap.model import Dataset, Project, RootSchema
from slidetap.model.batch import BatchCreate
from slidetap.model.item import Sample
from slidetap.model.schema.item_schema import SampleSchema
from slidetap.services import DatabaseService

MORE_THAN_PARAMETERS = 70_000
"""More uids than SQLite (32,766) or PostgreSQL (65,535) takes parameters."""


@pytest.fixture()
def sample_schema(schema: RootSchema) -> SampleSchema:
    return next(iter(schema.samples.values()))


@pytest.fixture()
def sample_uids(
    stored_database_service: DatabaseService,
    sample_schema: SampleSchema,
    dataset: Dataset,
    project: Project,
) -> list[UUID]:
    """Two samples stored, by uid."""
    with stored_database_service.get_session() as session:
        stored_database_service.add_dataset(session, dataset)
        stored_database_service.add_project(session, project)
        batch = stored_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        )
        return [
            stored_database_service.add_item(
                session,
                Sample(
                    uid=uuid4(),
                    identifier=identifier,
                    dataset_uid=dataset.uid,
                    batch_uid=batch.uid,
                    schema_uid=sample_schema.uid,
                ),
                [],
                [],
            ).uid
            for identifier in ("first", "second")
        ]


@pytest.mark.integration
class TestUidsFilter:
    def test_more_uids_than_a_statement_takes_parameters_are_filtered_by(
        self,
        stored_database_service: DatabaseService,
        sample_schema: SampleSchema,
        sample_uids: list[UUID],
    ):
        # Arrange
        wanted = sample_uids[0]
        uids = [wanted, *(uuid4() for _ in range(MORE_THAN_PARAMETERS))]

        # Act
        with stored_database_service.get_session() as session:
            found = [
                sample.uid
                for sample in stored_database_service.get_samples(
                    session, sample_schema, uids=uids
                )
            ]
            count = stored_database_service.get_item_count(
                session, sample_schema, uids=uids
            )

        # Assert
        assert found == [wanted]
        assert count == 1
