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

"""Tests for `VerificationService`.

Against a real SQLite database: which units a round can draw, and whether a
saved descendant makes a decision stale, are answered by queries and by walking
what hangs under a unit.
"""

import datetime
import random
from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from decoy import Decoy, matchers
from slidetap_example import ExampleSchema

from slidetap.model import (
    BatchCreate,
    BatchStatus,
    BatchValidation,
    Dataset,
    NotAllowedActionError,
    Project,
    ReviewIssueSource,
    ReviewLayout,
    ReviewStatus,
    ReviewUnitSchema,
    RootSchema,
    Sample,
    VerificationDecision,
    VerificationPolicy,
    VerificationPopulation,
    VerificationRoundCreate,
    VerificationState,
    VerificationSuggestionBasis,
    VerificationVerdict,
)
from slidetap.model.table import RelationFilter, RelationFilterType
from slidetap.services import (
    BatchService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
    VerificationService,
)


@pytest.fixture()
def policy() -> VerificationPolicy | None:
    return VerificationPolicy(required=True, default_size=2)


@pytest.fixture()
def root(schema: ExampleSchema, policy: VerificationPolicy | None) -> RootSchema:
    """The example root, with the case as what is reviewed and verified."""
    return schema.model_copy(
        update={
            "review_unit": ReviewUnitSchema(
                schema_uid=schema.case_schema_uid,
                layout=ReviewLayout(uid=uuid4(), name="review"),
                verification=policy,
            )
        }
    )


@pytest.fixture()
def schema_service(
    root: RootSchema, schema_service_of: Callable[..., SchemaService]
) -> SchemaService:
    return schema_service_of(root)


@pytest.fixture()
def review_service(
    schema_service: SchemaService, stored_database_service: DatabaseService
) -> ReviewService:
    return ReviewService(
        schema_service,
        ValidationService(schema_service, stored_database_service),
        stored_database_service,
    )


@pytest.fixture()
def verification_service(
    schema_service: SchemaService,
    stored_database_service: DatabaseService,
    review_service: ReviewService,
) -> VerificationService:
    return VerificationService(schema_service, stored_database_service, review_service)


@pytest.fixture()
def batch_service(
    decoy: Decoy,
    schema_service: SchemaService,
    stored_database_service: DatabaseService,
    review_service: ReviewService,
    verification_service: VerificationService,
) -> BatchService:
    """With every batch valid, so that what holds one back is verifying it."""
    validation_service = decoy.mock(cls=ValidationService)
    decoy.when(
        validation_service.get_validation_for_batch(matchers.Anything())
    ).then_return(BatchValidation(valid=True, uid=uuid4(), non_valid_items=[]))
    return BatchService(
        schema_service,
        validation_service,
        stored_database_service,
        review_service,
        verification_service,
    )


@pytest.fixture()
def batch_status() -> BatchStatus:
    return BatchStatus.IMAGE_POST_PROCESSING_COMPLETE


@pytest.fixture()
def specimens_per_case() -> list[int]:
    """How many specimens each case of the batch holds, one entry per case."""
    return [1, 1, 1, 1, 1, 1]


@pytest.fixture()
def batch_uid(
    stored_database_service: DatabaseService,
    root: RootSchema,
    batch_status: BatchStatus,
) -> UUID:
    dataset = Dataset(uid=uuid4(), name="dataset", schema_uid=root.dataset.uid)
    project = Project(
        uid=uuid4(),
        name="project",
        root_schema_uid=root.uid,
        schema_uid=root.project.uid,
        dataset_uid=dataset.uid,
        created=datetime.datetime(2026, 1, 1),
    )
    with stored_database_service.get_session() as session:
        stored_database_service.add_dataset(session, dataset)
        stored_database_service.add_project(session, project)
        batch = stored_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        )
        batch.status = batch_status
        session.commit()
        return batch.uid


@pytest.fixture()
def cases(
    stored_database_service: DatabaseService,
    schema: ExampleSchema,
    batch_uid: UUID,
    specimens_per_case: list[int],
) -> dict[str, UUID]:
    """The cases of the batch by identifier, each with its specimens."""
    case_uids: dict[str, UUID] = {}
    with stored_database_service.get_session() as session:
        batch = stored_database_service.get_batch(session, batch_uid)
        for number, specimen_count in enumerate(specimens_per_case, start=1):
            identifier = f"case-{number}"
            case = Sample(
                uid=uuid4(),
                identifier=identifier,
                dataset_uid=batch.project.dataset_uid,
                batch_uid=batch_uid,
                schema_uid=schema.case_schema_uid,
            )
            stored_database_service.add_item(session, case, [], [])
            session.flush()
            for specimen_number in range(1, specimen_count + 1):
                specimen = Sample(
                    uid=uuid4(),
                    identifier=f"{identifier}-{specimen_number}",
                    dataset_uid=batch.project.dataset_uid,
                    batch_uid=batch_uid,
                    schema_uid=schema.specimen_schema_uid,
                    parents={schema.case_to_specimen_relation.uid: [case.uid]},
                )
                stored_database_service.add_item(session, specimen, [], [])
            case_uids[identifier] = case.uid
        session.commit()
    return case_uids


def _deselect(database_service: DatabaseService, item_uid: UUID) -> None:
    with database_service.get_session() as session:
        database_service.get_item(session, item_uid).selected = False
        session.commit()


def _rename_specimen_of(
    database_service: DatabaseService, schema: ExampleSchema, case_uid: UUID
) -> None:
    with database_service.get_session() as session:
        case = database_service.get_item(session, case_uid)
        next(iter(database_service.get_children(case))).name = "renamed"
        session.commit()


def _deselect_specimen_of(
    database_service: DatabaseService, schema: ExampleSchema, case_uid: UUID
) -> None:
    with database_service.get_session() as session:
        case = database_service.get_item(session, case_uid)
        next(iter(database_service.get_children(case))).selected = False
        session.commit()


def _add_specimen_to(
    database_service: DatabaseService, schema: ExampleSchema, case_uid: UUID
) -> None:
    with database_service.get_session() as session:
        case = database_service.get_item(session, case_uid)
        specimen = Sample(
            uid=uuid4(),
            identifier=f"{case.identifier}-added",
            dataset_uid=case.dataset_uid,
            batch_uid=case.batch_uid,
            schema_uid=schema.specimen_schema_uid,
            parents={schema.case_to_specimen_relation.uid: [case_uid]},
        )
        database_service.add_item(session, specimen, [], [])
        session.commit()


def _flag_validate_and_lock(
    database_service: DatabaseService, schema: ExampleSchema, case_uid: UUID
) -> None:
    """Bookkeeping that leaves what the case holds as it was."""
    with database_service.get_session() as session:
        case = database_service.get_item(session, case_uid)
        case.review_status = ReviewStatus.FLAGGED
        case.valid_attributes = not case.valid_attributes
        for specimen in database_service.get_children(case):
            specimen.locked = True
        session.commit()


def _decide_all(verification_service: VerificationService, batch_uid: UUID) -> None:
    """Pass everything pending."""
    for entry in verification_service.get(batch_uid).entries:
        if entry.state != VerificationState.PENDING:
            continue
        verification_service.decide(
            entry.uid, VerificationDecision(verdict=VerificationVerdict.PASSED)
        )


@pytest.mark.integration
class TestVerificationService:
    @pytest.mark.parametrize("policy", [None])
    def test_a_root_without_a_policy_verifies_nothing(
        self,
        verification_service: VerificationService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Act
        verification = verification_service.get(batch_uid)

        # Assert
        assert verification.verified is False
        assert verification.blocking == []
        with pytest.raises(NotAllowedActionError):
            verification_service.draw(batch_uid, VerificationRoundCreate())

    def test_draws_the_suggested_number_of_units(
        self,
        verification_service: VerificationService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Act
        drawn = verification_service.draw(batch_uid, VerificationRoundCreate())

        # Assert
        verification = verification_service.get(batch_uid)
        assert drawn.drawn == 2
        assert drawn.number == 1
        assert drawn.population_size == 6
        assert verification.population_size == 6
        assert verification.undrawn == 4
        assert {entry.state for entry in verification.entries} == {
            VerificationState.PENDING
        }

    def test_a_draw_can_be_replayed_from_its_recorded_seed(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        root: RootSchema,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        """What a seed draws depends on the units, not on the order the
        database returns them in, so an audit can tell what should have been
        drawn."""
        # Arrange
        with stored_database_service.get_session() as session:
            undrawn = stored_database_service.get_undrawn_unit_uids(
                session, root.samples[schema.case_schema_uid], batch_uid
            )

        # Act
        drawn_round = verification_service.draw(
            batch_uid, VerificationRoundCreate(size=3)
        )

        # Assert
        expected = set(random.Random(drawn_round.seed).sample(undrawn, 3))  # noqa: S311
        drawn = {
            entry.unit_uid for entry in verification_service.get(batch_uid).entries
        }
        assert drawn == expected

    def test_a_later_round_draws_what_earlier_ones_left(
        self,
        verification_service: VerificationService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Act
        verification_service.draw(batch_uid, VerificationRoundCreate(size=4))
        second = verification_service.draw(batch_uid, VerificationRoundCreate(size=4))

        # Assert
        verification = verification_service.get(batch_uid)
        assert second.drawn == 2
        assert second.number == 2
        assert len({entry.unit_uid for entry in verification.entries}) == 6
        with pytest.raises(NotAllowedActionError):
            verification_service.draw(batch_uid, VerificationRoundCreate())

    def test_a_draw_racing_another_for_the_same_units_is_refused(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        cases: dict[str, UUID],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """As when two draws read what was left before either was saved."""
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate(size=2))
        drawn = [
            entry.unit_uid for entry in verification_service.get(batch_uid).entries
        ]
        monkeypatch.setattr(
            stored_database_service,
            "get_undrawn_unit_uids",
            lambda *_, **__: drawn,
        )

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="Another draw"):
            verification_service.draw(batch_uid, VerificationRoundCreate(size=2))

    def test_units_out_of_the_project_are_not_drawn(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        _deselect(stored_database_service, cases["case-1"])

        # Act
        drawn = verification_service.draw(batch_uid, VerificationRoundCreate(size=6))

        # Assert
        assert drawn.drawn == 5
        assert cases["case-1"] not in {
            entry.unit_uid for entry in verification_service.get(batch_uid).entries
        }

    @pytest.mark.parametrize("specimens_per_case", [[1, 2, 1, 3, 1, 2]])
    def test_draws_from_the_population_asked_for(
        self,
        verification_service: VerificationService,
        schema: ExampleSchema,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        """Cases with more than one specimen, as a follow-up on one that
        failed would ask for."""
        # Arrange
        population = VerificationPopulation(
            relation_filters=[
                RelationFilter(
                    relation_schema_uid=schema.specimen_schema_uid,
                    relation_type=RelationFilterType.CHILD,
                    min_count=2,
                )
            ]
        )

        # Act
        drawn = verification_service.draw(
            batch_uid, VerificationRoundCreate(size=10, population=population)
        )

        # Assert
        assert drawn.population_size == 3
        assert drawn.population == population
        assert {
            entry.identifier for entry in verification_service.get(batch_uid).entries
        } == {"case-2", "case-4", "case-6"}

    @pytest.mark.parametrize("batch_status", [BatchStatus.IMAGE_POST_PROCESSING])
    def test_a_batch_still_processing_is_not_verified_yet(
        self,
        verification_service: VerificationService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Act & Assert
        with pytest.raises(NotAllowedActionError):
            verification_service.draw(batch_uid, VerificationRoundCreate())

    def test_a_required_verification_blocks_until_every_unit_is_decided(
        self,
        verification_service: VerificationService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        blocked_before_drawing = verification_service.get(batch_uid).blocking
        verification_service.draw(batch_uid, VerificationRoundCreate())
        blocked_while_pending = verification_service.get(batch_uid).blocking

        # Act
        _decide_all(verification_service, batch_uid)

        # Assert
        assert len(blocked_before_drawing) == 1
        assert len(blocked_while_pending) == 1
        assert verification_service.get(batch_uid).blocking == []

    def test_failing_raises_an_issue_and_passing_again_settles_it(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate(size=1))
        entry = verification_service.get(batch_uid).entries[0]

        # Act
        failed = verification_service.decide(
            entry.uid,
            VerificationDecision(
                verdict=VerificationVerdict.FAILED, reason="Wrong stain"
            ),
        )
        with stored_database_service.get_session() as session:
            issues = [
                issue.model
                for issue in stored_database_service.get_review_issues(
                    session, entry.unit_uid
                )
            ]
            flagged = stored_database_service.get_item(
                session, entry.unit_uid
            ).review_status
        blocked_while_failed = verification_service.get(batch_uid).blocking
        passed = verification_service.decide(
            entry.uid, VerificationDecision(verdict=VerificationVerdict.PASSED)
        )

        # Assert
        assert failed.state == VerificationState.FAILED
        assert [issue.source for issue in issues] == [ReviewIssueSource.VERIFICATION]
        assert issues[0].reason == "Failed verification: Wrong stain"
        assert flagged == ReviewStatus.FLAGGED
        assert len(blocked_while_failed) == 1
        assert passed.state == VerificationState.PASSED
        assert passed.failed_at == failed.failed_at
        assert passed.reason == "Wrong stain"
        with stored_database_service.get_session() as session:
            assert (
                list(stored_database_service.get_review_issues(session, entry.unit_uid))
                == []
            )
            assert (
                stored_database_service.get_item(session, entry.unit_uid).review_status
                == ReviewStatus.NOT_REVIEWED
            )
        verification = verification_service.get(batch_uid)
        assert verification.blocking == []
        assert verification.rounds[0].failed == 1

    @pytest.mark.parametrize(
        "policy", [VerificationPolicy(required=False, default_size=2)]
    )
    def test_a_failed_unit_blocks_even_where_verifying_is_not_required(
        self,
        verification_service: VerificationService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        nothing_drawn = verification_service.get(batch_uid).blocking
        verification_service.draw(batch_uid, VerificationRoundCreate())
        pending = verification_service.get(batch_uid).blocking
        entry = verification_service.get(batch_uid).entries[0]

        # Act
        verification_service.decide(
            entry.uid,
            VerificationDecision(verdict=VerificationVerdict.FAILED, reason="Bad"),
        )

        # Assert
        assert nothing_drawn == []
        assert pending == []
        assert len(verification_service.get(batch_uid).blocking) == 1

    def test_a_failed_unit_taken_out_of_the_project_no_longer_blocks(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate(size=1))
        entry = verification_service.get(batch_uid).entries[0]
        verification_service.decide(
            entry.uid,
            VerificationDecision(verdict=VerificationVerdict.FAILED, reason="Bad"),
        )

        # Act
        _deselect(stored_database_service, entry.unit_uid)

        # Assert
        verification = verification_service.get(batch_uid)
        assert verification.entries[0].state == VerificationState.REMOVED
        # What is left is making up for it, not the failure.
        assert len(verification.blocking) == 1
        assert verification.blocking[0].startswith("Draw 1 more")
        assert verification.rounds[0].failed == 1
        with pytest.raises(NotAllowedActionError):
            verification_service.decide(
                entry.uid,
                VerificationDecision(verdict=VerificationVerdict.PASSED),
            )

    @pytest.mark.parametrize(
        "change", [_rename_specimen_of, _deselect_specimen_of, _add_specimen_to]
    )
    def test_changing_under_a_unit_after_it_was_decided_asks_for_a_recheck(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        batch_uid: UUID,
        cases: dict[str, UUID],
        change: Callable[[DatabaseService, ExampleSchema, UUID], None],
    ):
        """However it is changed: what was decided on is no longer there."""
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate(size=1))
        _decide_all(verification_service, batch_uid)
        entry = verification_service.get(batch_uid).entries[0]

        # Act
        change(stored_database_service, schema, entry.unit_uid)

        # Assert
        verification = verification_service.get(batch_uid)
        assert verification.entries[0].state == VerificationState.NEEDS_RECHECK
        assert len(verification.blocking) == 1

    def test_deleting_another_batch_holding_what_is_under_a_unit_asks_for_a_recheck(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        """Deleted in bulk, which no flush sees, and the case has still lost
        a specimen."""
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate(size=1))
        entry = verification_service.get(batch_uid).entries[0]
        with stored_database_service.get_session() as session:
            case = stored_database_service.get_item(session, entry.unit_uid)
            other_batch = stored_database_service.add_batch(
                session,
                BatchCreate(name="other", project_uid=case.batch.project_uid),
            )
            session.flush()
            other_batch_uid = other_batch.uid
            stored_database_service.add_item(
                session,
                Sample(
                    uid=uuid4(),
                    identifier=f"{case.identifier}-other",
                    dataset_uid=case.dataset_uid,
                    batch_uid=other_batch_uid,
                    schema_uid=schema.specimen_schema_uid,
                    parents={schema.case_to_specimen_relation.uid: [case.uid]},
                ),
                [],
                [],
            )
            session.commit()
        _decide_all(verification_service, batch_uid)

        # Act
        with stored_database_service.get_session() as session:
            stored_database_service.delete_items_of_batches(session, [other_batch_uid])
            stored_database_service.delete_batch(session, other_batch_uid)
            session.commit()

        # Assert
        assert (
            verification_service.get(batch_uid).entries[0].state
            == VerificationState.NEEDS_RECHECK
        )

    def test_bookkeeping_under_a_unit_does_not_ask_for_a_recheck(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate(size=1))
        _decide_all(verification_service, batch_uid)
        entry = verification_service.get(batch_uid).entries[0]

        # Act
        _flag_validate_and_lock(stored_database_service, schema, entry.unit_uid)

        # Assert
        assert (
            verification_service.get(batch_uid).entries[0].state
            == VerificationState.PASSED
        )

    def test_units_taken_out_after_they_were_drawn_are_made_up_for(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        """Taking every drawn unit out leaves nothing verified, which a
        required verification does not let through."""
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate(size=2))
        _decide_all(verification_service, batch_uid)
        for entry in verification_service.get(batch_uid).entries:
            _deselect(stored_database_service, entry.unit_uid)

        # Act
        blocked = verification_service.get(batch_uid).blocking
        verification_service.draw(batch_uid, VerificationRoundCreate(size=1))
        _decide_all(verification_service, batch_uid)

        # Assert
        assert len(blocked) == 1
        assert blocked[0].startswith("Draw 1 more")
        assert verification_service.get(batch_uid).blocking == []

    def test_a_batch_with_nothing_in_the_project_is_not_held_back(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        for case_uid in cases.values():
            _deselect(stored_database_service, case_uid)

        # Act
        verification = verification_service.get(batch_uid)

        # Assert
        assert verification.population_size == 0
        assert verification.blocking == []

    def test_completing_the_batch_is_refused_while_verification_blocks(
        self,
        verification_service: VerificationService,
        batch_service: BatchService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate())

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="not verified yet"):
            batch_service.set_as_locked(batch_uid)

    def test_deleting_the_batch_deletes_what_was_drawn(
        self,
        verification_service: VerificationService,
        stored_database_service: DatabaseService,
        batch_uid: UUID,
        cases: dict[str, UUID],
    ):
        # Arrange
        verification_service.draw(batch_uid, VerificationRoundCreate())

        # Act
        with stored_database_service.get_session() as session:
            stored_database_service.delete_items_of_batches(session, [batch_uid])
            stored_database_service.delete_batch(session, batch_uid)
            session.commit()

        # Assert
        with stored_database_service.get_session() as session:
            assert (
                stored_database_service.get_verification_rounds(session, batch_uid)
                == []
            )


@pytest.mark.unittest
class TestVerificationPolicy:
    @pytest.mark.parametrize(
        ["policy", "population", "expected"],
        [
            # ln(0.05) / ln(0.95), rounded up.
            (
                VerificationPolicy(target_confidence=0.95, target_defect_rate=0.05),
                400,
                59,
            ),
            (
                VerificationPolicy(target_confidence=0.95, target_defect_rate=0.05),
                20,
                20,
            ),
            (VerificationPolicy(default_fraction=0.1), 412, 42),
            (VerificationPolicy(default_size=5, minimum_size=10), 400, 10),
            (VerificationPolicy(), 400, 1),
            (VerificationPolicy(default_size=5), 0, 0),
        ],
    )
    def test_suggested_size(
        self, policy: VerificationPolicy, population: int, expected: int
    ):
        assert policy.suggested_size(population) == expected

    @pytest.mark.parametrize(
        ["policy", "population", "basis", "wanted", "size"],
        [
            (
                VerificationPolicy(target_confidence=0.95, target_defect_rate=0.05),
                400,
                VerificationSuggestionBasis.TARGETS,
                59,
                59,
            ),
            (
                VerificationPolicy(target_confidence=0.95, target_defect_rate=0.05),
                8,
                VerificationSuggestionBasis.TARGETS,
                59,
                8,
            ),
            (
                VerificationPolicy(default_fraction=0.1),
                412,
                VerificationSuggestionBasis.FRACTION,
                42,
                42,
            ),
            (
                VerificationPolicy(default_size=5, minimum_size=10),
                400,
                VerificationSuggestionBasis.SIZE,
                5,
                10,
            ),
            (VerificationPolicy(), 400, VerificationSuggestionBasis.MINIMUM, 1, 1),
        ],
    )
    def test_suggestion_says_what_it_comes_from(
        self,
        policy: VerificationPolicy,
        population: int,
        basis: VerificationSuggestionBasis,
        wanted: int,
        size: int,
    ):
        # Act
        suggestion = policy.suggestion(population)

        # Assert
        assert suggestion.basis == basis
        assert suggestion.wanted == wanted
        assert suggestion.size == size
        assert suggestion.undrawn == population
        assert suggestion.minimum_size == policy.minimum_size

    def test_targets_are_given_together(self):
        with pytest.raises(ValueError):
            VerificationPolicy(target_confidence=0.95)


@pytest.mark.unittest
class TestVerificationRequests:
    def test_a_reason_fits_in_the_issue_it_raises(self):
        """The issue holds 512 characters, and says what it is first."""
        # Arrange
        longest = 512 - len("Failed verification: ")

        # Act & Assert
        VerificationDecision(verdict=VerificationVerdict.FAILED, reason="x" * longest)
        with pytest.raises(ValueError):
            VerificationDecision(
                verdict=VerificationVerdict.FAILED, reason="x" * (longest + 1)
            )

    def test_a_draw_cannot_be_given_a_seed(self):
        """A seed the verifier picks could be one tried out beforehand to draw
        easy units."""
        # Arrange
        request = VerificationRoundCreate.model_validate({"size": 3, "seed": 42})

        # Act
        dumped = request.model_dump()

        # Assert
        assert "seed" not in dumped
