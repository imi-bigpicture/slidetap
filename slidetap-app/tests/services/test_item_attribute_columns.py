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

"""Tests that an attribute column filters and sorts on the selected value.

The selection travels from the table column menu as `AttributeValueField`, so
a filter on the mappable value must match items whose display value does not
contain the term, and the other way around.
"""

from uuid import UUID, uuid4

import pytest

from slidetap.database.attribute import DatabaseStringAttribute
from slidetap.model import (
    AttributeFilter,
    AttributeValueField,
    Dataset,
    Project,
    RootSchema,
)
from slidetap.model.batch import BatchCreate
from slidetap.model.item import Sample
from slidetap.model.schema.item_schema import SampleSchema
from slidetap.model.table import AttributeSort
from slidetap.services import DatabaseService

TAG = "attribute"

# Display and mappable value point at opposite samples, so a filter or sort
# using the wrong one gives the wrong sample.
SAMPLE_VALUES = {
    "first": ("beta display", "alfa mappable"),
    "second": ("alfa display", "beta mappable"),
}


@pytest.fixture()
def sample_schema(schema: RootSchema) -> SampleSchema:
    return next(iter(schema.samples.values()))


def add_samples(
    database_service: DatabaseService,
    sample_schema: SampleSchema,
    dataset: Dataset,
    project: Project,
) -> dict[str, UUID]:
    """Add a sample per entry in `SAMPLE_VALUES`, return their uids by identifier."""
    uids: dict[str, UUID] = {}
    with database_service.get_session() as session:
        database_service.add_dataset(session, dataset)
        database_service.add_project(session, project)
        batch = database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        )
        for identifier, (display_value, mappable_value) in SAMPLE_VALUES.items():
            sample = Sample(
                uid=uuid4(),
                identifier=identifier,
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=sample_schema.uid,
            )
            attribute = DatabaseStringAttribute(
                TAG,
                uuid4(),
                original_value=display_value,
                display_value=display_value,
                mappable_value=mappable_value,
            )
            uids[identifier] = database_service.add_item(
                session, sample, [attribute], []
            ).uid
    return uids


@pytest.mark.integration
class TestAttributeValueField:
    @pytest.mark.parametrize(
        ("field", "expected_identifier"),
        [
            (AttributeValueField.DISPLAY, "first"),
            (AttributeValueField.MAPPABLE, "second"),
        ],
    )
    def test_filters_on_selected_field(
        self,
        sqlite_database_service: DatabaseService,
        sample_schema: SampleSchema,
        dataset: Dataset,
        project: Project,
        field: AttributeValueField,
        expected_identifier: str,
    ):
        # Arrange
        sample_uids = add_samples(
            sqlite_database_service, sample_schema, dataset, project
        )
        attribute_filter = AttributeFilter(tag=TAG, value="beta", field=field)

        # Act
        with sqlite_database_service.get_session() as session:
            samples = sqlite_database_service.get_samples(
                session,
                sample_schema,
                attributes_filters=[attribute_filter],
            )
            filtered_uids = [sample.uid for sample in samples]

        # Assert
        assert filtered_uids == [sample_uids[expected_identifier]]

    @pytest.mark.parametrize(
        ("field", "expected_identifiers"),
        [
            (AttributeValueField.DISPLAY, ["second", "first"]),
            (AttributeValueField.MAPPABLE, ["first", "second"]),
        ],
    )
    def test_sorts_on_selected_field(
        self,
        sqlite_database_service: DatabaseService,
        sample_schema: SampleSchema,
        dataset: Dataset,
        project: Project,
        field: AttributeValueField,
        expected_identifiers: list[str],
    ):
        # Arrange
        sample_uids = add_samples(
            sqlite_database_service, sample_schema, dataset, project
        )
        sort = AttributeSort(column=TAG, field=field, descending=False)

        # Act
        with sqlite_database_service.get_session() as session:
            samples = sqlite_database_service.get_samples(
                session,
                sample_schema,
                sorting=[sort],
            )
            sorted_uids = [sample.uid for sample in samples]

        # Assert
        assert sorted_uids == [
            sample_uids[identifier] for identifier in expected_identifiers
        ]
