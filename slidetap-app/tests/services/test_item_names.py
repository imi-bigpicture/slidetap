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

"""Tests that the names an item is stepped through by stay inside one batch.

`get_item_names` is what says which items come before and after the one being
read; answering with another batch's items would step out of the batch being
worked.
"""

from uuid import UUID, uuid4

import pytest

from slidetap.model import Dataset, Project, RootSchema
from slidetap.model.batch import BatchCreate
from slidetap.model.item import Sample
from slidetap.model.schema.item_schema import SampleSchema
from slidetap.services import DatabaseService


@pytest.fixture()
def sample_schema(schema: RootSchema) -> SampleSchema:
    return next(iter(schema.samples.values()))


def add_samples(
    database_service: DatabaseService,
    sample_schema: SampleSchema,
    dataset: Dataset,
    project: Project,
) -> dict[str, tuple[UUID, UUID]]:
    """A sample in each of two batches; their uids and batch uids by identifier."""
    added: dict[str, tuple[UUID, UUID]] = {}
    with database_service.get_session() as session:
        database_service.add_dataset(session, dataset)
        database_service.add_project(session, project)
        for identifier in ("first", "second"):
            batch = database_service.add_batch(
                session, BatchCreate(name=identifier, project_uid=project.uid)
            )
            sample = Sample(
                uid=uuid4(),
                identifier=identifier,
                pseudonym=identifier.upper(),
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=sample_schema.uid,
            )
            added[identifier] = (
                database_service.add_item(session, sample, [], []).uid,
                batch.uid,
            )
    return added


@pytest.mark.integration
class TestItemNames:
    def test_names_are_limited_to_the_batch(
        self,
        sqlite_database_service: DatabaseService,
        sample_schema: SampleSchema,
        dataset: Dataset,
        project: Project,
    ):
        # Arrange
        added = add_samples(sqlite_database_service, sample_schema, dataset, project)
        first_uid, first_batch_uid = added["first"]

        # Act
        with sqlite_database_service.get_session() as session:
            names = sqlite_database_service.get_item_names(
                session,
                sample_schema.uid,
                dataset.uid,
                first_batch_uid,
            )

        # Assert
        assert names == [(first_uid, "first", "FIRST")]

    def test_names_of_every_batch_without_one(
        self,
        sqlite_database_service: DatabaseService,
        sample_schema: SampleSchema,
        dataset: Dataset,
        project: Project,
    ):
        # Arrange
        added = add_samples(sqlite_database_service, sample_schema, dataset, project)

        # Act
        with sqlite_database_service.get_session() as session:
            names = sqlite_database_service.get_item_names(
                session, sample_schema.uid, dataset.uid
            )

        # Assert
        assert sorted(names) == sorted(
            (uid, identifier, identifier.upper())
            for identifier, (uid, _) in added.items()
        )
