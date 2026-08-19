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

"""Tests for `ReviewService`.

What is mocked is what the service talks to, since what is being pinned is
the decision it makes.
"""

from contextlib import nullcontext
from uuid import UUID, uuid4

import pytest
from decoy import Decoy, matchers
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseReviewIssue,
    DatabaseSample,
    NotAllowedActionError,
)
from slidetap.model import (
    MetadataSearchResult,
    ReviewIssueSource,
    ReviewLayout,
    ReviewStatus,
    ReviewUnitSchema,
    Sample,
    SampleSchema,
)
from slidetap.services import (
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
)


@pytest.fixture()
def session(decoy: Decoy) -> Session:
    return decoy.mock(cls=Session)


@pytest.fixture()
def case_schema_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def review_unit() -> bool:
    """Whether the item being reviewed is what a reviewer works through."""
    return True


@pytest.fixture()
def case_schema(decoy: Decoy, case_schema_uid: UUID) -> SampleSchema:
    case_schema = decoy.mock(cls=SampleSchema)
    decoy.when(case_schema.uid).then_return(case_schema_uid)
    return case_schema


@pytest.fixture()
def reviewed_schema(
    case_schema_uid: UUID, review_unit: bool
) -> ReviewUnitSchema | None:
    """What the schema declares is reviewed, as the schema service answers it."""
    if not review_unit:
        return None
    return ReviewUnitSchema(
        schema_uid=case_schema_uid,
        layout=ReviewLayout(uid=uuid4(), name="review"),
    )


@pytest.fixture()
def case(decoy: Decoy, case_schema_uid: UUID) -> DatabaseSample:
    case = decoy.mock(cls=DatabaseSample)
    decoy.when(case.uid).then_return(uuid4())
    decoy.when(case.identifier).then_return("PL1234-20")
    decoy.when(case.schema_uid).then_return(case_schema_uid)
    decoy.when(case.selected).then_return(True)
    decoy.when(case.valid).then_return(True)
    return case


@pytest.fixture()
def invalid_identifiers() -> list[str]:
    """What under the case is not valid and still in the project."""
    return []


@pytest.fixture()
def deselected_invalid_identifiers() -> list[str]:
    """The same, but taken out of the project by the curator."""
    return []


@pytest.fixture()
def descendants(
    decoy: Decoy,
    invalid_identifiers: list[str],
    deselected_invalid_identifiers: list[str],
) -> list:
    """What hangs under the case. Valid unless a test says otherwise."""

    def _descendant(decoy: Decoy, identifier: str, valid: bool, selected: bool = True):
        descendant = decoy.mock(cls=DatabaseSample)
        decoy.when(descendant.uid).then_return(uuid4())
        decoy.when(descendant.identifier).then_return(identifier)
        decoy.when(descendant.schema_uid).then_return(uuid4())
        decoy.when(descendant.valid).then_return(valid)
        decoy.when(descendant.selected).then_return(selected)
        return descendant

    return [
        _descendant(decoy, "PL1234-20-1", valid=True),
        *(
            _descendant(decoy, identifier, valid=False)
            for identifier in invalid_identifiers
        ),
        *(
            _descendant(decoy, identifier, valid=False, selected=False)
            for identifier in deselected_invalid_identifiers
        ),
    ]


@pytest.fixture()
def schema_service(
    decoy: Decoy,
    case_schema: SampleSchema,
    case_schema_uid: UUID,
    reviewed_schema: ReviewUnitSchema | None,
):
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.items).then_return({case_schema_uid: case_schema})
    decoy.when(schema_service.review_unit).then_return(reviewed_schema)
    return schema_service


@pytest.fixture()
def database_service(
    decoy: Decoy,
    session: Session,
    case: DatabaseSample,
    descendants: list,
) -> DatabaseService:
    database_service = decoy.mock(cls=DatabaseService)
    decoy.when(database_service.get_session(None)).then_return(nullcontext(session))
    # Passed on to whatever the service calls within its own session, which is
    # how flagging reaches flag_for_review.
    decoy.when(database_service.get_session(session)).then_return(nullcontext(session))
    decoy.when(database_service.get_optional_item(session, case.uid)).then_return(case)
    # What hangs under the case is in the database too, which is how raising
    # something on one of them finds it.
    for descendant in descendants:
        decoy.when(
            database_service.get_optional_item(session, descendant.uid)
        ).then_return(descendant)
    decoy.when(database_service.walk_item_descendants(case)).then_return(
        [case, *descendants]
    )
    # Nothing has been raised on anything yet, which is the world every test
    # here starts in. A test about what happens when something is open says so.
    decoy.when(
        database_service.get_open_issues_for_item(
            session, matchers.Anything(), ReviewIssueSource.VALIDATION
        )
    ).then_return([])
    # Recording one answers with the row it wrote, which is what the service
    # hands back to whoever raised it.
    decoy.when(
        database_service.add_review_issue(
            session,
            matchers.Anything(),
            matchers.Anything(),
            matchers.Anything(),
            matchers.Anything(),
        )
    ).then_return(decoy.mock(cls=DatabaseReviewIssue))
    return database_service


@pytest.fixture()
def validation_service(decoy: Decoy) -> ValidationService:
    return decoy.mock(cls=ValidationService)


@pytest.fixture()
def review_service(
    schema_service, validation_service: ValidationService, database_service
) -> ReviewService:
    return ReviewService(
        schema_service=schema_service,
        validation_service=validation_service,
        database_service=database_service,
    )


@pytest.fixture()
def raised(
    decoy: Decoy,
    database_service: DatabaseService,
) -> list[tuple]:
    """What was recorded as raised, as (item, unit, reason, source).

    Recorded rather than rehearsed in both a `when` and a `verify`, so that the
    reason is asserted as the service worded it.
    """
    raised: list[tuple] = []

    def _record(_session, item, unit, reason, source):
        raised.append((item, unit, reason, source))
        return decoy.mock(cls=DatabaseReviewIssue)

    decoy.when(
        database_service.add_review_issue(
            matchers.Anything(),
            matchers.Anything(),
            matchers.Anything(),
            matchers.Anything(),
            matchers.Anything(),
        )
    ).then_do(_record)
    return raised


@pytest.mark.unittest
@pytest.mark.parametrize("invalid_identifiers", [["PL1234-20-16"]])
class TestUnitHoldingSomethingInvalid:
    def test_it_is_not_reviewed(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """The failure this guards against: a case signed off while something
        under it is invalid, which takes it out of the queue and leaves the
        invalid item for whoever tries to complete the batch to find."""
        # Arrange

        # Act & Assert
        with pytest.raises(NotAllowedActionError) as raised:
            review_service.set_review_status(case.uid, ReviewStatus.REVIEWED)
        assert "PL1234-20-16" in str(raised.value)

    def test_it_is_flagged_with_what_is_wrong(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """Refusing is not enough on its own: the reviewer asked for the case
        to be done with, and the answer has to stay on it."""
        # Arrange

        # Act
        with pytest.raises(NotAllowedActionError):
            review_service.set_review_status(case.uid, ReviewStatus.REVIEWED)

        # Assert
        assert case.review_status == ReviewStatus.FLAGGED
        assert "PL1234-20-16" in case.review_reason

    def test_asking_for_review_through_here_is_refused(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """Review is asked for by raising an issue on the item it is about, so
        that what was asked for is on record beside everything else open on the
        unit and can be settled one at a time. A flag written straight onto the
        unit says that somebody wanted something and nothing about what would
        settle it, which is what left cases sitting in the queue after the thing
        that flagged them had been dealt with."""
        # Arrange

        # Act
        with pytest.raises(NotAllowedActionError):
            review_service.set_review_status(
                case.uid, ReviewStatus.FLAGGED, reason="Looks wrong to me"
            )

        # Assert
        assert case.review_status != ReviewStatus.FLAGGED

    @pytest.mark.parametrize("review_unit", [False])
    def test_an_item_that_is_not_a_review_unit_is_reviewed_all_the_same(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """An item reviewed through the unit above it answers for nothing on
        its own, so nothing under it is checked."""
        # Arrange

        # Act
        review_service.set_review_status(case.uid, ReviewStatus.REVIEWED)

        # Assert
        assert case.review_status == ReviewStatus.REVIEWED


@pytest.mark.unittest
class TestUnitThatIsReady:
    def test_unit_with_everything_valid_is_reviewed(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        # Arrange

        # Act
        review_service.set_review_status(case.uid, ReviewStatus.REVIEWED)

        # Assert
        assert case.review_status == ReviewStatus.REVIEWED

    @pytest.mark.parametrize("deselected_invalid_identifiers", [["PL1234-20-16"]])
    def test_deselected_item_does_not_hold_the_unit_back(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """Taking an item out of the project is one of the two ways of dealing
        with it, and an item going nowhere cannot be curated into being valid.
        Counting it would leave the case impossible to sign off."""
        # Arrange

        # Act
        review_service.set_review_status(case.uid, ReviewStatus.REVIEWED)

        # Assert
        assert case.review_status == ReviewStatus.REVIEWED


@pytest.mark.unittest
@pytest.mark.unittest
class TestReviewUnitsInResult:
    """Which units an imported search result is taken to have produced."""

    def test_found_however_the_result_names_its_entry_item(
        self,
        review_service: ReviewService,
        case_schema_uid: UUID,
    ) -> None:
        """The failure this guards against: an importer naming something other
        than the review unit as its entry item, and every case it produced
        going unflagged with nothing said about it.

        Asked of the service directly: it is where the answer is decided, and
        going through ``add_search_result`` would test the persisting rather
        than the deciding.
        """
        # Arrange
        dataset_uid = uuid4()
        being = Sample(
            uid=uuid4(),
            identifier="B1",
            dataset_uid=dataset_uid,
            schema_uid=uuid4(),
        )
        case = Sample(
            uid=uuid4(),
            identifier="PL1234-20",
            dataset_uid=dataset_uid,
            schema_uid=case_schema_uid,
        )
        result = MetadataSearchResult.succeeded(
            identifier="PL1234-20",
            schema_uid=being.schema_uid,
            items=[being, case],
            item_uid=being.uid,
        )

        # Act
        units = list(review_service.review_unit_uids_in(result, {}))

        # Assert
        assert units == [case.uid]

    def test_every_unit_the_result_produced_is_found(
        self,
        review_service: ReviewService,
        case_schema_uid: UUID,
    ) -> None:
        # Arrange
        dataset_uid = uuid4()
        cases = [
            Sample(
                uid=uuid4(),
                identifier=identifier,
                dataset_uid=dataset_uid,
                schema_uid=case_schema_uid,
            )
            for identifier in ("PL1234-20", "PL1235-20")
        ]
        result = MetadataSearchResult.succeeded(
            identifier="two cases",
            schema_uid=case_schema_uid,
            items=cases,
            item_uid=cases[0].uid,
        )

        # Act
        units = list(review_service.review_unit_uids_in(result, {}))

        # Assert
        assert units == [case.uid for case in cases]


@pytest.mark.unittest
class TestNonValidItems:
    """What the reviewer is shown of what a flag refers to."""

    @pytest.mark.parametrize("invalid_identifiers", [["PL1234-20-16"]])
    def test_what_is_wrong_is_listed(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """The failure this guards against: a case flagged for an item the
        reviewer has no way to reach, because no panel happens to show that
        kind of item."""
        # Arrange

        # Act
        issues = review_service.get_non_valid_items(case.uid)

        # Assert
        assert [issue.identifier for issue in issues] == ["PL1234-20-16"]

    def test_a_unit_with_nothing_wrong_lists_nothing(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        # Arrange

        # Act
        issues = review_service.get_non_valid_items(case.uid)

        # Assert
        assert issues == []

    @pytest.mark.parametrize("deselected_invalid_identifiers", [["PL1234-20-16"]])
    def test_an_item_taken_out_of_the_project_is_not_listed(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """Read the same way as the flag that sends the reviewer here, or the
        list would not account for the flag."""
        # Arrange

        # Act
        issues = review_service.get_non_valid_items(case.uid)

        # Assert
        assert issues == []

    @pytest.mark.parametrize("review_unit", [False])
    @pytest.mark.parametrize("invalid_identifiers", [["PL1234-20-16"]])
    def test_an_item_that_is_not_a_review_unit_lists_nothing(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """It answers for nothing on its own, so there is nothing to show."""
        # Arrange

        # Act
        issues = review_service.get_non_valid_items(case.uid)

        # Assert
        assert issues == []


@pytest.mark.unittest
class TestFlagOnImport:
    """What the driver does with a unit an importer has just finished, where
    that importer brings in everything the unit is made of."""

    @pytest.mark.parametrize("invalid_identifiers", [["PL1234-20-16"]])
    def test_unit_holding_an_invalid_item_is_flagged(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """The failure this guards against: a case that came in missing an
        image sitting in the queue as if nothing were wrong, found only by
        whoever opens it."""
        # Arrange

        # Act
        flagged = review_service.flag_review_unit_if_invalid(case.uid)

        # Assert
        assert flagged
        assert case.review_status == ReviewStatus.FLAGGED
        assert "PL1234-20-16" in case.review_reason

    @pytest.mark.parametrize(
        "invalid_identifiers", [["PL1234-20-16", "PL1234-20-17"]]
    )
    def test_each_invalid_item_is_raised_on_by_itself(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
        raised: list[tuple],
    ) -> None:
        """One issue per item rather than one per unit: they are settled one at
        a time, as each is dealt with, and a count of what is wrong under a case
        cannot be settled at all."""
        # Arrange

        # Act
        review_service.flag_review_unit_if_invalid(case.uid)

        # Assert
        assert [item.identifier for item, _, _, _ in raised] == [
            "PL1234-20-16",
            "PL1234-20-17",
        ]
        assert {unit for _, unit, _, _ in raised} == {case}
        assert {source for _, _, _, source in raised} == {
            ReviewIssueSource.VALIDATION
        }

    def test_unit_with_everything_valid_is_left_alone(
        self,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        # Arrange

        # Act
        flagged = review_service.flag_review_unit_if_invalid(case.uid)

        # Assert
        assert not flagged

    @pytest.mark.parametrize("invalid_identifiers", [["PL1234-20-16"]])
    def test_a_reason_already_given_is_kept(
        self,
        decoy: Decoy,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """An importer that found something specific — an image on a slide
        stained with something else — has said something more useful than a
        count of invalid items, and writing over it would lose it."""
        # Arrange
        decoy.when(case.review_status).then_return(ReviewStatus.FLAGGED)
        case.review_reason = "1 images match no slide: PL1234-20-16"

        # Act
        review_service.flag_review_unit_if_invalid(case.uid)

        # Assert
        assert case.review_reason == "1 images match no slide: PL1234-20-16"


@pytest.mark.unittest
class TestValidityTransitions:
    """What the callers of validation report when an item crosses between
    valid and not, and what the queue does about it.

    The point of recording it: a unit flagged because something under it was
    not valid leaves the queue when that is dealt with, without anybody having
    to work out what it was flagged for.
    """

    @pytest.fixture()
    def specimen_schema_uid(self) -> UUID:
        return uuid4()

    @pytest.fixture()
    def specimen(self, decoy: Decoy, specimen_schema_uid: UUID) -> DatabaseSample:
        """A specimen under the case, with an attribute nothing could map."""
        specimen = decoy.mock(cls=DatabaseSample)
        decoy.when(specimen.uid).then_return(uuid4())
        decoy.when(specimen.identifier).then_return("PL1234-20-1")
        decoy.when(specimen.schema_uid).then_return(specimen_schema_uid)
        decoy.when(specimen.valid_attributes).then_return(False)
        decoy.when(specimen.valid_relations).then_return(True)
        decoy.when(specimen.valid_pseudonym).then_return(True)
        return specimen

    @pytest.fixture()
    def issue(self, decoy: Decoy) -> DatabaseReviewIssue:
        """What validation raised on the specimen, still open."""
        issue = decoy.mock(cls=DatabaseReviewIssue)
        decoy.when(issue.uid).then_return(uuid4())
        return issue

    @pytest.fixture(autouse=True)
    def _specimen_under_the_case(
        self,
        decoy: Decoy,
        session: Session,
        database_service: DatabaseService,
        schema_service: SchemaService,
        specimen: DatabaseSample,
        specimen_schema_uid: UUID,
        case: DatabaseSample,
        case_schema_uid: UUID,
        issue: DatabaseReviewIssue,
        raised: list[tuple],
    ) -> None:
        """The specimen is found, sits under the case, and the case is what
        answers for it."""
        decoy.when(schema_service.review_unit_covers(specimen_schema_uid)).then_return(
            True
        )
        decoy.when(
            database_service.get_optional_item(session, specimen.uid)
        ).then_return(specimen)
        decoy.when(
            database_service.get_ancestor(specimen, {case_schema_uid})
        ).then_return(case)
        decoy.when(
            database_service.get_optional_review_issue(session, issue.uid)
        ).then_return(issue)

    def test_an_item_going_invalid_is_raised_on_the_case(
        self,
        decoy: Decoy,
        session: Session,
        database_service: DatabaseService,
        review_service: ReviewService,
        specimen: DatabaseSample,
        case: DatabaseSample,
        raised: list[tuple],
    ) -> None:
        """Raised on the item and answered on the case, with what is wrong
        named rather than counted."""
        # Arrange
        decoy.when(
            database_service.get_open_issues_for_item(
                session, specimen.uid, ReviewIssueSource.VALIDATION
            )
        ).then_return([])

        # Act
        review_service.item_became_invalid(specimen.uid)

        # Assert
        assert raised == [
            (specimen, case, "Not valid: attributes", ReviewIssueSource.VALIDATION)
        ]
        assert case.review_status == ReviewStatus.FLAGGED

    def test_an_item_already_raised_on_is_not_raised_on_again(
        self,
        decoy: Decoy,
        session: Session,
        database_service: DatabaseService,
        review_service: ReviewService,
        specimen: DatabaseSample,
        issue: DatabaseReviewIssue,
        raised: list[tuple],
    ) -> None:
        """The failure this guards against: a batch remap validating the same
        item once per attribute, leaving a row for every attribute it has."""
        # Arrange
        decoy.when(
            database_service.get_open_issues_for_item(
                session, specimen.uid, ReviewIssueSource.VALIDATION
            )
        ).then_return([issue])

        # Act
        review_service.item_became_invalid(specimen.uid)

        # Assert
        assert raised == []

    def test_an_item_going_valid_settles_it_and_clears_the_case(
        self,
        decoy: Decoy,
        session: Session,
        database_service: DatabaseService,
        review_service: ReviewService,
        specimen: DatabaseSample,
        case: DatabaseSample,
        issue: DatabaseReviewIssue,
    ) -> None:
        """What this whole thing is for: the mapping that was missing is added,
        the specimen is valid, and the case leaves the queue by itself."""
        # Arrange
        decoy.when(case.review_status).then_return(ReviewStatus.FLAGGED)
        decoy.when(
            database_service.get_open_issues_for_item(
                session, specimen.uid, ReviewIssueSource.VALIDATION
            )
        ).then_return([issue])
        decoy.when(database_service.get_review_issues(session, case.uid)).then_return(
            []
        )

        # Act
        cleared = review_service.item_became_valid(specimen.uid)

        # Assert
        assert cleared
        assert issue.resolved_at is not None

    def test_something_else_open_keeps_the_case_in_the_queue(
        self,
        decoy: Decoy,
        session: Session,
        database_service: DatabaseService,
        review_service: ReviewService,
        specimen: DatabaseSample,
        case: DatabaseSample,
        issue: DatabaseReviewIssue,
    ) -> None:
        """A case is flagged for whatever anybody raised on it, so settling one
        of them says nothing about the rest."""
        # Arrange
        raised_by_a_colleague = decoy.mock(cls=DatabaseReviewIssue)
        decoy.when(case.review_status).then_return(ReviewStatus.FLAGGED)
        decoy.when(
            database_service.get_open_issues_for_item(
                session, specimen.uid, ReviewIssueSource.VALIDATION
            )
        ).then_return([issue])
        decoy.when(database_service.get_review_issues(session, case.uid)).then_return(
            [raised_by_a_colleague]
        )

        # Act
        cleared = review_service.item_became_valid(specimen.uid)

        # Assert
        assert not cleared
        assert issue.resolved_at is not None

    def test_a_case_already_reviewed_is_left_alone(
        self,
        decoy: Decoy,
        session: Session,
        database_service: DatabaseService,
        review_service: ReviewService,
        case: DatabaseSample,
    ) -> None:
        """It has been answered for, and nothing here re-opens that."""
        # Arrange
        decoy.when(case.review_status).then_return(ReviewStatus.REVIEWED)
        decoy.when(database_service.get_review_issues(session, case.uid)).then_return(
            []
        )

        # Act
        cleared = review_service.clear_flag_if_nothing_open(case.uid)

        # Assert
        assert not cleared
        assert case.review_status == ReviewStatus.REVIEWED


@pytest.mark.unittest
class TestSettlingWhatAnImportFixed:
    """An import runs again, and the second run brings in what was missing the
    first time. What was raised for it has to be settled, or the case sits in
    the queue for something that is no longer wrong with it."""

    @pytest.fixture()
    def specimen(self, decoy: Decoy) -> DatabaseSample:
        specimen = decoy.mock(cls=DatabaseSample)
        decoy.when(specimen.uid).then_return(uuid4())
        decoy.when(specimen.identifier).then_return("PL1234-20-1")
        return specimen

    @pytest.fixture()
    def raised_by_validation(
        self, decoy: Decoy, specimen: DatabaseSample
    ) -> DatabaseReviewIssue:
        issue = decoy.mock(cls=DatabaseReviewIssue)
        decoy.when(issue.uid).then_return(uuid4())
        decoy.when(issue.item).then_return(specimen)
        decoy.when(issue.item_uid).then_return(specimen.uid)
        decoy.when(issue.source).then_return(ReviewIssueSource.VALIDATION)
        return issue

    @pytest.fixture(autouse=True)
    def _the_issue_is_open_on_the_case(
        self,
        decoy: Decoy,
        session: Session,
        database_service: DatabaseService,
        case: DatabaseSample,
        specimen: DatabaseSample,
        raised_by_validation: DatabaseReviewIssue,
    ) -> None:
        decoy.when(
            database_service.get_optional_item(session, specimen.uid)
        ).then_return(specimen)
        decoy.when(
            database_service.get_optional_review_issue(session, raised_by_validation.uid)
        ).then_return(raised_by_validation)
        decoy.when(database_service.get_review_issues(session, case.uid)).then_return(
            [raised_by_validation]
        )
        decoy.when(case.review_status).then_return(ReviewStatus.FLAGGED)

    def test_an_item_valid_again_is_settled(
        self,
        decoy: Decoy,
        session: Session,
        review_service: ReviewService,
        validation_service: ValidationService,
        specimen: DatabaseSample,
        case: DatabaseSample,
        raised_by_validation: DatabaseReviewIssue,
    ) -> None:
        # Arrange
        decoy.when(
            validation_service.item_is_valid_for_now(specimen, session)
        ).then_return(True)

        # Act
        settled = review_service.settle_what_is_valid_under(case.uid)

        # Assert
        assert settled == 1
        assert raised_by_validation.resolved_at is not None

    def test_an_item_still_not_valid_is_left_alone(
        self,
        decoy: Decoy,
        session: Session,
        review_service: ReviewService,
        validation_service: ValidationService,
        specimen: DatabaseSample,
        case: DatabaseSample,
        raised_by_validation: DatabaseReviewIssue,
    ) -> None:
        """The import brought something in, but not what this was raised for."""
        # Arrange
        decoy.when(
            validation_service.item_is_valid_for_now(specimen, session)
        ).then_return(False)

        # Act
        settled = review_service.settle_what_is_valid_under(case.uid)

        # Assert — nothing was settled; an unresolved issue cannot be asserted
        # on directly, since an unstubbed mock answers with a mock rather than
        # with the None a live row would hold.
        assert settled == 0

    def test_what_somebody_asked_to_have_looked_at_is_not_settled(
        self,
        decoy: Decoy,
        session: Session,
        review_service: ReviewService,
        validation_service: ValidationService,
        specimen: DatabaseSample,
        case: DatabaseSample,
        raised_by_validation: DatabaseReviewIssue,
    ) -> None:
        """A colleague's issue is settled by somebody looking at it, whatever
        the items say — an import cannot answer it."""
        # Arrange
        decoy.when(raised_by_validation.source).then_return(ReviewIssueSource.USER)
        decoy.when(
            validation_service.item_is_valid_for_now(specimen, session)
        ).then_return(True)

        # Act
        settled = review_service.settle_what_is_valid_under(case.uid)

        # Assert — nothing was settled; an unresolved issue cannot be asserted
        # on directly, since an unstubbed mock answers with a mock rather than
        # with the None a live row would hold.
        assert settled == 0
