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

"""What deleting a batch leaves behind.

Against a real SQLite database rather than mocks: the delete is a set of bulk
statements, and what is being pinned is which rows each of them matches. SQLite
does not enforce foreign keys, so a dependent table the delete misses is not
caught by the database here; it is caught by counting its rows.
"""

import datetime
from uuid import UUID, uuid4

import pytest
from slidetap_example import ExampleSchema
from sqlalchemy import FromClause, func, select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseAttribute,
    DatabaseImage,
    DatabaseImageFile,
    DatabaseItem,
    DatabaseMetadataSearchItem,
    DatabaseObservation,
    DatabaseReviewIssue,
    DatabaseSample,
    DatabaseStringAttribute,
    DatabaseUnmappedValue,
    NotAllowedActionError,
)
from slidetap.database.item import DatabaseTag
from slidetap.model import (
    BatchCreate,
    BatchStatus,
    Dataset,
    ImageFormat,
    Project,
    ProjectStatus,
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
def default_batch(
    sqlite_database_service: DatabaseService,
    stored_project: Project,
) -> UUID:
    """The project's default batch, which shared items are handed to."""
    with sqlite_database_service.get_session() as session:
        default = sqlite_database_service.add_batch(
            session, BatchCreate(name="default", project_uid=stored_project.uid)
        )
        session.flush()
        sqlite_database_service.get_project(
            session, stored_project.uid
        ).default_batch_uid = default.uid
        session.commit()
        return default.uid


@pytest.fixture()
def batches(
    sqlite_database_service: DatabaseService,
    stored_project: Project,
    default_batch: UUID,
) -> tuple[UUID, UUID]:
    """Batch A, the one deleted, and batch B, which stays."""
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
    attributes: list[DatabaseAttribute] | None = None,
    tags: list[DatabaseTag] | None = None,
) -> DatabaseSample:
    stored = DatabaseSample(
        dataset_uid,
        batch_uid,
        schema_uid,
        identifier,
        parents=parents,
        attributes=attributes,
        tags=tags,
    )
    session.add(stored)
    session.flush()
    return stored


def image(
    session: Session,
    dataset_uid: UUID,
    batch_uid: UUID,
    schema_uid: UUID,
    identifier: str,
    slide: DatabaseSample,
    folder_path: str | None = None,
) -> DatabaseImage:
    stored = DatabaseImage(
        dataset_uid,
        batch_uid,
        schema_uid,
        identifier,
        ImageFormat.DICOM_WSI,
        samples=slide,
        folder_path=folder_path,
        thumbnail_path=None if folder_path is None else f"{folder_path}.jpeg",
    )
    session.add(stored)
    session.flush()
    return stored


def mark_deleting(database_service: DatabaseService, batch_uid: UUID) -> None:
    with database_service.get_session() as session:
        database_service.get_batch(session, batch_uid).status = BatchStatus.DELETING
        session.commit()


def count(session: Session, table: FromClause) -> int:
    return session.scalar(select(func.count()).select_from(table)) or 0


def stored_sample(session: Session, uid: UUID) -> DatabaseSample:
    stored = session.get(DatabaseSample, uid)
    assert stored is not None
    return stored


def identifiers(session: Session) -> set[str]:
    return {item.identifier for item in session.scalars(select(DatabaseItem))}


@pytest.mark.integration
class TestDeleteBatch:
    def test_everything_of_the_batch_is_gone(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema: ExampleSchema,
        dataset: Dataset,
        batches: tuple[UUID, UUID],
    ):
        """Every table hanging off an item is cleared, and only for the batch.

        SQLite does not enforce foreign keys, so a table the delete misses
        would leave orphans here and fail the delete on Postgres. Counting
        every dependent table is what stands in for the database.
        """
        # Arrange
        first, second = batches
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
                attributes=[DatabaseStringAttribute("tag", uuid4(), "value")],
                tags=[DatabaseTag("tag-a")],
            )
            specimen = sample(
                session,
                dataset.uid,
                first,
                schema.specimen_schema_uid,
                "specimen-a",
                parents=[case],
            )
            block = sample(
                session,
                dataset.uid,
                first,
                schema.block_schema_uid,
                "block-a",
                parents=[specimen],
            )
            slide = sample(
                session,
                dataset.uid,
                first,
                schema.slide_schema_uid,
                "slide-a",
                parents=[block],
            )
            stored_image = image(
                session, dataset.uid, first, schema.image_schema_uid, "image-a", slide
            )
            session.add(DatabaseImageFile(stored_image, "image.dcm"))
            session.add(
                DatabaseAnnotation(
                    dataset.uid, first, uuid4(), "annotation-a", image=stored_image
                )
            )
            session.add(
                DatabaseObservation(
                    dataset.uid,
                    first,
                    schema.observation_schema_uid,
                    "observation-a",
                    item=case,
                )
            )
            session.flush()
            attribute = next(iter(case.attributes))
            session.add(
                DatabaseUnmappedValue(
                    uid=uuid4(),
                    root_attribute_uid=attribute.uid,
                    schema_uid=attribute.schema_uid,
                    value="value",
                )
            )
            sqlite_database_service.add_review_issue(
                session, stored_image, slide, "wrong", ReviewIssueSource.VALIDATION
            )
            session.add(
                DatabaseMetadataSearchItem(
                    batch_uid=first,
                    identifier="case-a",
                    schema_uid=schema.case_schema_uid,
                    item_uid=case.uid,
                )
            )
            sample(
                session,
                dataset.uid,
                second,
                schema.patient_schema_uid,
                "patient-b",
                attributes=[DatabaseStringAttribute("tag", uuid4(), "value")],
                tags=[DatabaseTag("tag-b")],
            )
            session.commit()
        mark_deleting(sqlite_database_service, first)

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert sqlite_database_service.get_optional_batch(session, first) is None
            assert identifiers(session) == {"patient-b"}
            for table in (
                DatabaseSample.__table__,
                DatabaseItem.__table__,
                DatabaseAttribute.__table__,
                DatabaseStringAttribute.__table__,
                DatabaseItem.item_to_tag,
            ):
                assert count(session, table) == 1, table
            assert count(session, DatabaseTag.__table__) == 2
            for table in (
                DatabaseImage.__table__,
                DatabaseAnnotation.__table__,
                DatabaseObservation.__table__,
                DatabaseImageFile.__table__,
                DatabaseUnmappedValue.__table__,
                DatabaseReviewIssue.__table__,
                DatabaseMetadataSearchItem.__table__,
                DatabaseSample.sample_to_sample,
                DatabaseImage.sample_to_image,
            ):
                assert count(session, table) == 0, table

    def test_item_another_batch_hangs_off_moves_to_the_default_batch(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema: ExampleSchema,
        dataset: Dataset,
        default_batch: UUID,
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
                second,
                schema.case_schema_uid,
                "case-b",
                parents=[patient],
            )
            session.commit()
            patient_uid = patient.uid
        mark_deleting(sqlite_database_service, first)

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, patient_uid).batch_uid == default_batch

    def test_item_nothing_else_hangs_off_is_deleted(
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
        mark_deleting(sqlite_database_service, first)

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert identifiers(session) == set()

    def test_handing_over_reaches_up_through_the_batch(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema: ExampleSchema,
        dataset: Dataset,
        default_batch: UUID,
        batches: tuple[UUID, UUID],
    ):
        """A case another batch's specimen hangs off is handed over, and so is
        the patient the case hangs off: once the case is outside the batch, the
        patient is one another batch hangs off."""
        # Arrange
        first, second = batches
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
            specimen = sample(
                session,
                dataset.uid,
                second,
                schema.specimen_schema_uid,
                "specimen-b",
                parents=[case],
            )
            session.commit()
            patient_uid, case_uid, specimen_uid = patient.uid, case.uid, specimen.uid
        mark_deleting(sqlite_database_service, first)

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, patient_uid).batch_uid == default_batch
            assert stored_sample(session, case_uid).batch_uid == default_batch
            assert {
                parent.uid for parent in stored_sample(session, specimen_uid).parents
            } == {case_uid}

    def test_slide_another_batch_images_is_handed_over_with_its_image(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema: ExampleSchema,
        dataset: Dataset,
        default_batch: UUID,
        batches: tuple[UUID, UUID],
    ):
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            slide = sample(
                session, dataset.uid, first, schema.slide_schema_uid, "slide-a"
            )
            image(
                session, dataset.uid, second, schema.image_schema_uid, "image-b", slide
            )
            session.commit()
            slide_uid = slide.uid
        mark_deleting(sqlite_database_service, first)

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, slide_uid).batch_uid == default_batch
            assert count(session, DatabaseImage.sample_to_image) == 1

    def test_issue_on_a_handed_over_item_answered_elsewhere_is_kept(
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
            case_b = sample(
                session,
                dataset.uid,
                second,
                schema.case_schema_uid,
                "case-b",
                parents=[patient],
            )
            sqlite_database_service.add_review_issue(
                session, patient, case_b, "wrong", ReviewIssueSource.METADATA_IMPORTER
            )
            session.commit()
        mark_deleting(sqlite_database_service, first)

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            issue = session.scalars(select(DatabaseReviewIssue)).one()
            assert issue.item.identifier == "patient-1"
            assert issue.review_unit.identifier == "case-b"

    def test_issue_answered_on_a_deleted_item_goes_with_it(
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
            case_a = sample(
                session,
                dataset.uid,
                first,
                schema.case_schema_uid,
                "case-a",
                parents=[patient],
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
                session, case_b, case_a, "wrong", ReviewIssueSource.METADATA_IMPORTER
            )
            session.commit()
        mark_deleting(sqlite_database_service, first)

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert count(session, DatabaseReviewIssue.__table__) == 0
            assert identifiers(session) == {"patient-1", "case-b"}

    def test_handed_over_item_is_validated_again(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema: ExampleSchema,
        dataset: Dataset,
        default_batch: UUID,
        batches: tuple[UUID, UUID],
    ):
        """A block whose slide is in another batch is handed over, and so is
        the specimen it hangs off, which the block cannot be left without.
        What the block's relations are worth is recomputed from what is left,
        rather than kept from before the delete."""
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            specimen = sample(
                session, dataset.uid, first, schema.specimen_schema_uid, "specimen-a"
            )
            block = sample(
                session,
                dataset.uid,
                first,
                schema.block_schema_uid,
                "block-a",
                parents=[specimen],
            )
            # Stale: with a specimen above and a slide below, the block's
            # relations are valid, and the delete is what says so.
            block.valid_relations = False
            sample(
                session,
                dataset.uid,
                second,
                schema.slide_schema_uid,
                "slide-b",
                parents=[block],
            )
            session.commit()
            block_uid, specimen_uid = block.uid, specimen.uid
        mark_deleting(sqlite_database_service, first)

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            assert stored_sample(session, specimen_uid).batch_uid == default_batch
            assert stored_sample(session, block_uid).valid_relations is True

    def test_returns_the_paths_of_the_deleted_images_only(
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
            slide = sample(
                session, dataset.uid, first, schema.slide_schema_uid, "slide-a"
            )
            image(
                session,
                dataset.uid,
                first,
                schema.image_schema_uid,
                "image-a",
                slide,
                folder_path="/processing/image-a",
            )
            held = image(
                session,
                dataset.uid,
                first,
                schema.image_schema_uid,
                "image-held",
                slide,
                folder_path="/processing/image-held",
            )
            session.add(
                DatabaseAnnotation(
                    dataset.uid, second, uuid4(), "annotation-b", image=held
                )
            )
            session.commit()
        mark_deleting(sqlite_database_service, first)

        # Act
        paths = batch_service.delete(first)

        # Assert
        assert [
            (path.identifier, path.folder_path, path.thumbnail_path) for path in paths
        ] == [("image-a", "/processing/image-a", "/processing/image-a.jpeg")]

    def test_refuses_a_batch_not_marked_as_deleting(
        self,
        batch_service: BatchService,
        batches: tuple[UUID, UUID],
    ):
        first, _ = batches
        with pytest.raises(NotAllowedActionError):
            batch_service.delete(first)

    def test_project_without_default_batch_cannot_delete(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        stored_project: Project,
        batches: tuple[UUID, UUID],
    ):
        first, _ = batches
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.get_project(
                session, stored_project.uid
            ).default_batch_uid = None
            session.commit()
        mark_deleting(sqlite_database_service, first)
        with pytest.raises(ValueError):
            batch_service.delete(first)


@pytest.mark.integration
class TestDeleteBatchOfProject:
    def test_a_project_being_deleted_stays_deleting(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        stored_project: Project,
        default_batch: UUID,
        batches: tuple[UUID, UUID],
    ):
        """A batch of a project on its way out that goes first leaves the rest
        curated; that is not what completes the project."""
        # Arrange
        first, second = batches
        with sqlite_database_service.get_session() as session:
            for uid in (default_batch, second):
                sqlite_database_service.get_batch(
                    session, uid
                ).status = BatchStatus.LOCKED
            sqlite_database_service.get_batch(
                session, first
            ).status = BatchStatus.DELETING
            sqlite_database_service.get_project(
                session, stored_project.uid
            ).status = ProjectStatus.DELETING
            session.commit()

        # Act
        batch_service.delete(first)

        # Assert
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, stored_project.uid)
            assert project.status == ProjectStatus.DELETING


@pytest.mark.integration
class TestSetAsDeleting:
    def test_refuses_the_default_batch(
        self,
        batch_service: BatchService,
        default_batch: UUID,
    ):
        with pytest.raises(NotAllowedActionError, match="default"):
            batch_service.set_as_deleting(default_batch)

    def test_refuses_a_batch_of_a_project_being_deleted(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        stored_project: Project,
        batches: tuple[UUID, UUID],
    ):
        first, _ = batches
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.get_project(
                session, stored_project.uid
            ).status = ProjectStatus.DELETING
            session.commit()

        with pytest.raises(NotAllowedActionError, match="project is being deleted"):
            batch_service.set_as_deleting(first)

    @pytest.mark.parametrize(
        "status",
        [
            BatchStatus.INITIALIZED,
            BatchStatus.METADATA_SEARCH_COMPLETE,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
            BatchStatus.IMAGE_POST_PROCESSING_COMPLETE,
            BatchStatus.FAILED,
            BatchStatus.DELETING,
            BatchStatus.DELETED,
        ],
    )
    def test_marks_a_batch_nothing_holds(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        batches: tuple[UUID, UUID],
        status: BatchStatus,
    ):
        first, _ = batches
        with sqlite_database_service.get_session() as session:
            batch = sqlite_database_service.get_batch(session, first)
            batch.status = status
            batch.status_message = "what went wrong last time"
            session.commit()

        marked = batch_service.set_as_deleting(first)

        assert marked.status == BatchStatus.DELETING
        assert marked.status_message is None

    @pytest.mark.parametrize(
        "status",
        [
            BatchStatus.METADATA_SEARCHING,
            BatchStatus.IMAGE_PRE_PROCESSING,
            BatchStatus.IMAGE_POST_PROCESSING,
            BatchStatus.IMAGE_STORING,
            BatchStatus.LOCKED,
            BatchStatus.COMPLETED,
        ],
    )
    def test_refuses_a_batch_a_worker_holds_or_that_is_curated(
        self,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        batches: tuple[UUID, UUID],
        status: BatchStatus,
    ):
        first, _ = batches
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.get_batch(session, first).status = status
            session.commit()

        with pytest.raises(NotAllowedActionError):
            batch_service.set_as_deleting(first)
        with sqlite_database_service.get_session() as session:
            assert sqlite_database_service.get_batch(session, first).status == status
