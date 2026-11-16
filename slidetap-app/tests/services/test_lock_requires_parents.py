"""Tests for locking a batch with a sample that lacks a parent it requires.

Against a real SQLite database, with what validation stored saying everything
is valid: a link can go without the sample under it being validated again, and
the lock is what stops such a sample from being exported.
"""

import datetime
from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from decoy import Decoy, matchers
from slidetap_example import ExampleSchema

from slidetap.application_policy import ApplicationPolicy
from slidetap.model import (
    BatchCreate,
    BatchStatus,
    BatchValidation,
    Dataset,
    NotAllowedActionError,
    Project,
    Sample,
)
from slidetap.services import (
    BatchService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
    VerificationService,
)


@pytest.fixture()
def schema_service(
    schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
) -> SchemaService:
    return schema_service_of(schema)


@pytest.fixture()
def validation_service(decoy: Decoy) -> ValidationService:
    """Saying every batch is valid, as it does when what it stored is stale."""
    validation_service = decoy.mock(cls=ValidationService)
    decoy.when(
        validation_service.get_validation_for_batch(matchers.Anything())
    ).then_return(BatchValidation(valid=True, uid=uuid4(), non_valid_items=[]))
    return validation_service


@pytest.fixture()
def batch_service(
    schema_service: SchemaService,
    stored_database_service: DatabaseService,
    validation_service: ValidationService,
) -> BatchService:
    review_service = ReviewService(
        schema_service, validation_service, stored_database_service
    )
    return BatchService(
        schema_service,
        validation_service,
        stored_database_service,
        review_service,
        VerificationService(schema_service, stored_database_service, review_service),
        application_policy=ApplicationPolicy(),
    )


@pytest.fixture()
def batch_uid(stored_database_service: DatabaseService, schema: ExampleSchema) -> UUID:
    dataset = Dataset(uid=uuid4(), name="dataset", schema_uid=schema.dataset.uid)
    project = Project(
        uid=uuid4(),
        name="project",
        root_schema_uid=schema.uid,
        schema_uid=schema.project.uid,
        dataset_uid=dataset.uid,
        created=datetime.datetime(2026, 1, 1),
    )
    with stored_database_service.get_session() as session:
        stored_database_service.add_dataset(session, dataset)
        stored_database_service.add_project(session, project)
        batch = stored_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        )
        batch.status = BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
        session.commit()
        return batch.uid


class Samples:
    """Adds samples to the batch, each under the parent it is given."""

    def __init__(
        self, database_service: DatabaseService, schema: ExampleSchema, batch_uid: UUID
    ):
        self._database_service = database_service
        self._schema = schema
        self._batch_uid = batch_uid

    def add(
        self,
        identifier: str,
        schema_uid: UUID,
        parent: tuple[UUID, UUID] | None = None,
    ) -> UUID:
        """Add a sample, under ``parent`` as (relation uid, parent uid)."""
        with self._database_service.get_session() as session:
            batch = self._database_service.get_batch(session, self._batch_uid)
            sample = Sample(
                uid=uuid4(),
                identifier=identifier,
                dataset_uid=batch.project.dataset_uid,
                batch_uid=self._batch_uid,
                schema_uid=schema_uid,
                parents={} if parent is None else {parent[0]: [parent[1]]},
            )
            self._database_service.add_item(session, sample, [], [])
            session.commit()
            return sample.uid

    def block(self) -> UUID:
        """A block under a specimen, a case and a patient."""
        schema = self._schema
        patient = self.add("patient", schema.patient_schema_uid)
        case = self.add(
            "case",
            schema.case_schema_uid,
            (schema.patient_to_case_relation.uid, patient),
        )
        specimen = self.add(
            "specimen",
            schema.specimen_schema_uid,
            (schema.case_to_specimen_relation.uid, case),
        )
        return self.add(
            "block",
            schema.block_schema_uid,
            (schema.specimen_to_block_relation.uid, specimen),
        )


@pytest.fixture()
def samples(
    stored_database_service: DatabaseService, schema: ExampleSchema, batch_uid: UUID
) -> Samples:
    return Samples(stored_database_service, schema, batch_uid)


@pytest.mark.unittest
class TestLockRequiresParents:
    def test_a_slide_on_no_block_refuses_the_lock(
        self,
        decoy: Decoy,
        batch_service: BatchService,
        validation_service: ValidationService,
        samples: Samples,
        schema: ExampleSchema,
        batch_uid: UUID,
    ):
        # Arrange
        block = samples.block()
        samples.add(
            "slide-1",
            schema.slide_schema_uid,
            (schema.block_to_slide_relation.uid, block),
        )
        orphan = samples.add("slide-2", schema.slide_schema_uid)

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match=r"1 samples .*\(slide-2\)"):
            batch_service.set_as_locked(batch_uid)
        decoy.verify(
            validation_service.validate_relations_for([orphan], matchers.Anything())
        )
        assert batch_service.get(batch_uid).status == (
            BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
        )

    def test_a_slide_on_a_deselected_block_refuses_the_lock(
        self,
        batch_service: BatchService,
        stored_database_service: DatabaseService,
        samples: Samples,
        schema: ExampleSchema,
        batch_uid: UUID,
    ):
        # Arrange
        block = samples.block()
        samples.add(
            "slide-1",
            schema.slide_schema_uid,
            (schema.block_to_slide_relation.uid, block),
        )
        with stored_database_service.get_session() as session:
            stored_database_service.get_item(session, block).selected = False
            session.commit()

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="slide-1"):
            batch_service.set_as_locked(batch_uid)

    def test_a_batch_whose_samples_have_their_parents_is_locked(
        self,
        batch_service: BatchService,
        samples: Samples,
        schema: ExampleSchema,
        batch_uid: UUID,
    ):
        # Arrange
        block = samples.block()
        samples.add(
            "slide-1",
            schema.slide_schema_uid,
            (schema.block_to_slide_relation.uid, block),
        )

        # Act
        batch = batch_service.set_as_locked(batch_uid)

        # Assert
        assert batch.status == BatchStatus.LOCKED
