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

"""What a batch searched again does to items another batch hangs off.

Against a real SQLite database rather than mocks: what is being pinned is what
the delete leaves behind, which is decided by the ORM cascades and by which
rows the queries match.

The shape throughout is the one that made this a bug: a patient (the biological
being) created by the first batch's case, with the second batch's case hanging
off the same patient, since a patient is stored once for the dataset.
"""

import datetime
from uuid import UUID

import pytest
from slidetap_example import ExampleSchema
from sqlalchemy import select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseItem,
    DatabaseReviewIssue,
    DatabaseSample,
)
from slidetap.model import (
    BatchCreate,
    Dataset,
    Project,
    ReviewIssueSource,
)
from slidetap.services import (
    BatchService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
)


@pytest.fixture()
def schema_service(schema: ExampleSchema) -> SchemaService:
    return SchemaService(schema)


@pytest.fixture()
def batch_service(
    schema_service: SchemaService,
    sqlite_database_service: DatabaseService,
) -> BatchService:
    validation_service = ValidationService(schema_service, sqlite_database_service)
    review_service = ReviewService(
        schema_service, validation_service, sqlite_database_service
    )
    return BatchService(
        schema_service,
        validation_service,
        sqlite_database_service,
        review_service,
    )


@pytest.fixture()
def stored_project(
    sqlite_database_service: DatabaseService,
    dataset: Dataset,
    project: Project,
) -> Project:
    with sqlite_database_service.get_session() as session:
        sqlite_database_service.add_dataset(session, dataset)
        sqlite_database_service.add_project(session, project)
        session.commit()
    return project


@pytest.fixture()
def batches(
    sqlite_database_service: DatabaseService,
    stored_project: Project,
) -> tuple[UUID, UUID]:
    """Batch A, searched first, and batch B, searched after it."""
    with sqlite_database_service.get_session() as session:
        first = sqlite_database_service.add_batch(
            session, BatchCreate(name="A", project_uid=stored_project.uid)
        )
        first.created = datetime.datetime(2026, 1, 1)
        second = sqlite_database_service.add_batch(
            session, BatchCreate(name="B", project_uid=stored_project.uid)
        )
        second.created = datetime.datetime(2026, 2, 1)
        session.commit()
        return first.uid, second.uid


def sample(
    session: Session,
    dataset_uid: UUID,
    batch_uid: UUID,
    schema_uid: UUID,
    identifier: str,
    parents: list[DatabaseSample] | None = None,
) -> DatabaseSample:
    stored = DatabaseSample(
        dataset_uid, batch_uid, schema_uid, identifier, parents=parents
    )
    session.add(stored)
    session.flush()
    return stored


def clear_batch(
    database_service: DatabaseService,
    schema_service: SchemaService,
    batch_uid: UUID,
) -> None:
    """The part of a search that clears out what the last one left."""
    with database_service.get_session() as session:
        for item_schema in schema_service.items.values():
            database_service.delete_items(session, item_schema, batch_uid)


def stored_sample(session: Session, uid: UUID) -> DatabaseSample:
    sample = session.get(DatabaseSample, uid)
    assert sample is not None
    return sample


def identifiers(session: Session) -> set[str]:
    return {item.identifier for item in session.scalars(select(DatabaseItem))}


@pytest.mark.integration
class TestMoveSharedItemsToOtherBatch:
    def test_item_another_batch_hangs_off_is_moved(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            sample(
                session,
                dataset.uid,
                first,
                schema.case_schema_uid,
                "case-a",
                parents=[patient],
            )
            sample(
                session,
                dataset.uid,
                second,
                schema.case_schema_uid,
                "case-b",
                parents=[patient],
            )
            session.commit()
            patient_uid = patient.uid

        # Act
        moved = batch_service.move_shared_items_to_other_batch(first)

        # Assert
        assert moved == 1
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, patient_uid).batch_uid == second

    def test_item_only_this_batch_hangs_off_is_left(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, _ = batches
        with sqlite_database_service.get_session() as session:
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            sample(
                session,
                dataset.uid,
                first,
                schema.case_schema_uid,
                "case-a",
                parents=[patient],
            )
            session.commit()
            patient_uid = patient.uid

        # Act
        moved = batch_service.move_shared_items_to_other_batch(first)

        # Assert
        assert moved == 0
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, patient_uid).batch_uid == first

    def test_moved_to_earliest_of_the_batches_hanging_off_it(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        stored_project: Project,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            third = sqlite_database_service.add_batch(
                session, BatchCreate(name="C", project_uid=stored_project.uid)
            )
            third.created = datetime.datetime(2026, 3, 1)
            session.flush()
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            sample(
                session,
                dataset.uid,
                third.uid,
                schema.case_schema_uid,
                "case-c",
                parents=[patient],
            )
            sample(
                session,
                dataset.uid,
                second,
                schema.case_schema_uid,
                "case-b",
                parents=[patient],
            )
            session.commit()
            patient_uid = patient.uid

        # Act
        batch_service.move_shared_items_to_other_batch(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, patient_uid).batch_uid == second

    def test_search_again_keeps_the_other_batch_whole(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            sample(
                session,
                dataset.uid,
                first,
                schema.case_schema_uid,
                "case-a",
                parents=[patient],
            )
            sample(
                session,
                dataset.uid,
                second,
                schema.case_schema_uid,
                "case-b",
                parents=[patient],
            )
            session.commit()

        # Act
        batch_service.move_shared_items_to_other_batch(first)
        clear_batch(sqlite_database_service, schema_service, first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert identifiers(session) == {"patient-1", "case-b"}
            case_b = session.scalars(
                select(DatabaseSample).where(DatabaseSample.identifier == "case-b")
            ).one()
            assert {parent.identifier for parent in case_b.parents} == {"patient-1"}

    def test_search_again_keeps_issues_on_a_moved_item(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            case_b = sample(
                session,
                dataset.uid,
                second,
                schema.case_schema_uid,
                "case-b",
                parents=[patient],
            )
            sqlite_database_service.add_review_issue(
                session,
                patient,
                case_b,
                "Two patients with the same identifier",
                ReviewIssueSource.METADATA_IMPORTER,
            )
            session.commit()

        # Act
        batch_service.move_shared_items_to_other_batch(first)
        clear_batch(sqlite_database_service, schema_service, first)

        # Assert
        with sqlite_database_service.get_session() as session:
            issue = session.scalars(select(DatabaseReviewIssue)).one()
            assert issue.item.identifier == "patient-1"
            assert issue.review_unit.identifier == "case-b"


@pytest.mark.integration
class TestDeleteItemsLeavesOtherBatchesAlone:
    def test_child_in_another_batch_survives_its_parent(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            case_b = sample(
                session,
                dataset.uid,
                second,
                schema.case_schema_uid,
                "case-b",
                parents=[patient],
            )
            session.commit()
            case_b_uid = case_b.uid

        # Act
        clear_batch(sqlite_database_service, schema_service, first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, case_b_uid).parents == set()
            assert identifiers(session) == {"case-b"}

    def test_child_in_the_same_batch_goes_with_it(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, _ = batches
        with sqlite_database_service.get_session() as session:
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            case = sample(
                session,
                dataset.uid,
                first,
                schema.case_schema_uid,
                "case-a",
                parents=[patient],
            )
            sample(
                session,
                dataset.uid,
                first,
                schema.specimen_schema_uid,
                "specimen-a",
                parents=[case],
            )
            session.commit()

        # Act
        clear_batch(sqlite_database_service, schema_service, first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert identifiers(session) == set()
            assert session.execute(select(DatabaseSample.sample_to_sample)).all() == []


@pytest.mark.integration
class TestDeleteBatchSharedItems:
    def test_item_another_batch_hangs_off_moves_to_the_default_batch(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        stored_project: Project,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            default = sqlite_database_service.add_batch(
                session, BatchCreate(name="default", project_uid=stored_project.uid)
            )
            session.flush()
            default_uid = default.uid
            sqlite_database_service.get_project(
                session, stored_project.uid
            ).default_batch_uid = default_uid
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            sample(
                session,
                dataset.uid,
                second,
                schema.case_schema_uid,
                "case-b",
                parents=[patient],
            )
            session.commit()
            patient_uid = patient.uid

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, patient_uid).batch_uid == default_uid

    def test_item_nothing_else_hangs_off_is_deleted(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        stored_project: Project,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, _ = batches
        with sqlite_database_service.get_session() as session:
            default = sqlite_database_service.add_batch(
                session, BatchCreate(name="default", project_uid=stored_project.uid)
            )
            session.flush()
            sqlite_database_service.get_project(
                session, stored_project.uid
            ).default_batch_uid = default.uid
            patient = sample(
                session, dataset.uid, first, schema.patient_schema_uid, "patient-1"
            )
            sample(
                session,
                dataset.uid,
                first,
                schema.case_schema_uid,
                "case-a",
                parents=[patient],
            )
            session.commit()

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert identifiers(session) == set()
