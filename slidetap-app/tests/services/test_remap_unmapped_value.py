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

"""Remapping the items that carry one unmapped value.

Against a real database, since what is being pinned is which rows the
query finds and what the remap leaves in `unmapped_value`.
"""

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from slidetap_example import ExampleSchema

from slidetap.database import DatabaseSample
from slidetap.model import (
    BatchCreate,
    BatchStatus,
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
    Project,
)
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
)
from slidetap.services.mapper_service import MapperService

PARAFFIN = Code(code="311731000", scheme="SCT", meaning="Paraffin wax")


@pytest.fixture()
def schema_service(
    schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
) -> SchemaService:
    return schema_service_of(schema)


@pytest.fixture()
def embedding_schema(schema: ExampleSchema) -> CodeAttributeSchema:
    attribute_schema = schema.block.attributes["embedding"]
    assert isinstance(attribute_schema, CodeAttributeSchema)
    return attribute_schema


@pytest.fixture()
def mapper_service(
    schema_service: SchemaService,
    stored_database_service: DatabaseService,
) -> MapperService:
    validation_service = ValidationService(schema_service, stored_database_service)
    review_service = ReviewService(
        schema_service, validation_service, stored_database_service
    )
    attribute_service = AttributeService(
        schema_service, validation_service, stored_database_service, review_service
    )
    return MapperService(
        attribute_service=attribute_service,
        validation_service=validation_service,
        schema_service=schema_service,
        database_service=stored_database_service,
        review_service=review_service,
    )


@pytest.fixture()
def stored_project(
    stored_database_service: DatabaseService,
    embedding_schema: CodeAttributeSchema,
    dataset: Dataset,
    project: Project,
) -> Project:
    """The project, with a mapper for embedding that knows "Paraffin"."""
    with stored_database_service.get_session() as session:
        group = stored_database_service.add_mapper_group(session, "default", True)
        mapper = stored_database_service.add_mapper(
            session, "embedding", embedding_schema.uid, embedding_schema.uid
        )
        session.flush()
        group.mappers.add(mapper)
        stored_database_service.add_mapping(
            session,
            mapper.uid,
            "^Paraffin$",
            CodeAttribute(
                uid=uuid4(), schema_uid=embedding_schema.uid, original_value=PARAFFIN
            ),
        )
        stored_database_service.add_dataset(session, dataset)
        session.flush()
        stored = project.model_copy(update={"mapper_groups": [group.uid]})
        stored_database_service.add_project(session, stored)
        session.commit()
    return stored


def add_batch(
    database_service: DatabaseService, project: Project, status: BatchStatus
) -> UUID:
    with database_service.get_session() as session:
        batch = database_service.add_batch(
            session, BatchCreate(name=str(status), project_uid=project.uid)
        )
        batch.status = status
        session.commit()
        return batch.uid


def add_block(
    database_service: DatabaseService,
    schema: ExampleSchema,
    embedding_schema: CodeAttributeSchema,
    project: Project,
    batch_uid: UUID,
    embedding: str,
) -> UUID:
    """A block whose embedding was imported as the given wording, unmapped."""
    with database_service.get_session() as session:
        attribute = database_service.add_attribute(
            session,
            CodeAttribute(
                uid=uuid4(), schema_uid=embedding_schema.uid, mappable_value=embedding
            ),
            embedding_schema,
        )
        block = DatabaseSample(
            project.dataset_uid,
            batch_uid,
            schema.block.uid,
            f"block {uuid4()}",
            attributes=[attribute],
        )
        session.add(block)
        session.commit()
        return attribute.uid


def unmapped(database_service: DatabaseService, project: Project) -> set[str]:
    with database_service.get_session() as session:
        return {
            value
            for _, value, _ in database_service.unmapped_value_counts(
                session, project.uid
            )
        }


@pytest.mark.integration
class TestRemapUnmappedValue:
    def test_the_items_carrying_the_value_are_mapped(
        self,
        stored_database_service: DatabaseService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        embedding_schema: CodeAttributeSchema,
        stored_project: Project,
    ):
        # Arrange
        batch_uid = add_batch(
            stored_database_service,
            stored_project,
            BatchStatus.METADATA_SEARCH_COMPLETE,
        )
        attribute_uids = [
            add_block(
                stored_database_service,
                schema,
                embedding_schema,
                stored_project,
                batch_uid,
                "Paraffin",
            )
            for _ in range(2)
        ]

        # Act
        result = mapper_service.remap_unmapped_value(
            stored_project.uid, embedding_schema.uid, "Paraffin"
        )

        # Assert
        assert result.remapped_items == 2
        assert result.skipped_items == 0
        with stored_database_service.get_session() as session:
            for attribute_uid in attribute_uids:
                attribute = stored_database_service.get_attribute(
                    session, attribute_uid
                )
                assert attribute.model.mapped_value == PARAFFIN
        assert unmapped(stored_database_service, stored_project) == set()

    def test_items_carrying_another_value_are_left(
        self,
        stored_database_service: DatabaseService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        embedding_schema: CodeAttributeSchema,
        stored_project: Project,
    ):
        # Arrange
        batch_uid = add_batch(
            stored_database_service,
            stored_project,
            BatchStatus.METADATA_SEARCH_COMPLETE,
        )
        for embedding in ("Paraffin", "Frozen"):
            add_block(
                stored_database_service,
                schema,
                embedding_schema,
                stored_project,
                batch_uid,
                embedding,
            )

        # Act
        result = mapper_service.remap_unmapped_value(
            stored_project.uid, embedding_schema.uid, "Paraffin"
        )

        # Assert
        assert result.remapped_items == 1
        assert unmapped(stored_database_service, stored_project) == {"Frozen"}

    def test_items_in_a_batch_being_processed_are_skipped(
        self,
        stored_database_service: DatabaseService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        embedding_schema: CodeAttributeSchema,
        stored_project: Project,
    ):
        # Arrange
        searching_uid = add_batch(
            stored_database_service, stored_project, BatchStatus.METADATA_SEARCHING
        )
        add_block(
            stored_database_service,
            schema,
            embedding_schema,
            stored_project,
            searching_uid,
            "Paraffin",
        )

        # Act
        result = mapper_service.remap_unmapped_value(
            stored_project.uid, embedding_schema.uid, "Paraffin"
        )

        # Assert
        assert result.remapped_items == 0
        assert result.skipped_items == 1
        assert unmapped(stored_database_service, stored_project) == {"Paraffin"}

    def test_only_the_given_batch_is_remapped(
        self,
        stored_database_service: DatabaseService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        embedding_schema: CodeAttributeSchema,
        stored_project: Project,
    ):
        # Arrange
        batch_uids = [
            add_batch(
                stored_database_service,
                stored_project,
                BatchStatus.METADATA_SEARCH_COMPLETE,
            )
            for _ in range(2)
        ]
        attribute_uids = [
            add_block(
                stored_database_service,
                schema,
                embedding_schema,
                stored_project,
                batch_uid,
                "Paraffin",
            )
            for batch_uid in batch_uids
        ]

        # Act
        result = mapper_service.remap_unmapped_value(
            stored_project.uid, embedding_schema.uid, "Paraffin", batch_uids[0]
        )

        # Assert
        assert result.remapped_items == 1
        with stored_database_service.get_session() as session:
            mapped, untouched = (
                stored_database_service.get_attribute(session, uid).model
                for uid in attribute_uids
            )
            assert mapped.mapped_value == PARAFFIN
            assert untouched.mapped_value is None
