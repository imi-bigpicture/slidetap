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

"""Verifying a batch: drawing review units at random and checking them by
hand before the batch is completed."""

import logging
import math
import random
import secrets
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseBatch,
    DatabaseVerificationEntry,
    DatabaseVerificationRound,
)
from slidetap.model import (
    BatchVerification,
    NotAllowedActionError,
    NotFoundError,
    ReviewIssueSource,
    VerificationDecision,
    VerificationEntry,
    VerificationPolicy,
    VerificationRound,
    VerificationRoundCreate,
    VerificationState,
    VerificationVerdict,
)
from slidetap.model.schema.item_schema import ItemSchema
from slidetap.model.verification import FAILED_VERIFICATION
from slidetap.services.database_service import DatabaseService
from slidetap.services.review_service import ReviewService
from slidetap.services.schema_service import SchemaService


class VerificationService:
    """Rounds of review units drawn from a batch, what a verifier decides about
    each, and whether that lets the batch be completed.

    What is verified is the review unit, as what is reviewed: a verifier is
    handed a case and judges the whole of it. A unit failed raises an issue on
    itself, so that it is fixed where everything else raised is answered, and
    is checked again here once it has been.
    """

    #: How many units a reason names before the rest are counted.
    _NAMED_UNITS = 5

    def __init__(
        self,
        schema_service: SchemaService,
        database_service: DatabaseService,
        review_service: ReviewService,
    ):
        self._schema_service = schema_service
        self._database_service = database_service
        self._review_service = review_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get(self, batch_uid: UUID, session: Session | None = None) -> BatchVerification:
        """How verifying a batch stands.

        Parameters
        ----------
        batch_uid: UUID
            The batch to tell about.
        session: Session | None
            Session to look in.

        Returns
        -------
        BatchVerification
            What was drawn and decided, and what holds the batch back. Not
            verified, and otherwise empty, where the root of the batch's project
            declares no verification policy.

        Raises
        ------
        NotFoundError
            There is no such batch.
        """
        with self._database_service.get_session(session) as session:
            batch = self._get_batch(session, batch_uid)
            found = self._policy_of(batch, session)
            if found is None:
                return BatchVerification(batch_uid=batch.uid, verified=False)
            policy, unit_schema = found
            rounds = self._database_service.get_verification_rounds(session, batch.uid)
            entries = self._entry_models(rounds)
            undrawn = self._database_service.count_undrawn_units(
                session, unit_schema, batch.uid
            )
            population_size = self._database_service.get_item_count(
                session, unit_schema, batch=batch.uid, selected=True
            )
            return BatchVerification(
                batch_uid=batch.uid,
                verified=True,
                required=policy.required,
                population_size=population_size,
                undrawn=undrawn,
                suggestion=policy.suggestion(undrawn),
                rounds=[
                    self._round_model(verification_round, number, policy)
                    for number, verification_round in enumerate(rounds, start=1)
                ],
                entries=entries,
                blocking=self._blocking(policy, population_size, entries),
            )

    def draw(
        self,
        batch_uid: UUID,
        request: VerificationRoundCreate,
        session: Session | None = None,
    ) -> VerificationRound:
        """Draw units of a batch at random to verify.

        Parameters
        ----------
        batch_uid: UUID
            The batch to draw from.
        request: VerificationRoundCreate
            How many to draw, as a count or a share of the units drawn from,
            and the policy's suggestion where neither is given; never fewer
            than the policy's minimum while there are that many. Which units to
            draw from, every unit in the project no round has drawn where no
            population is given. The entry the round follows up on, if any.
            The seed is always picked here at random, and recorded.
        session: Session | None
            Session to draw in.

        Returns
        -------
        VerificationRound
            The round drawn.

        Raises
        ------
        NotFoundError
            There is no such batch, or the entry the round follows up on is not
            one of the batch's.
        NotAllowedActionError
            The batch is not verified, is not done processing its images or is
            already completed, there is nothing left to draw, or another draw
            took some of the same units first.
        """
        with self._database_service.get_session(session) as session:
            batch = self._get_batch(session, batch_uid)
            policy, unit_schema = self._assert_can_verify(batch, session)
            if request.origin_entry_uid is not None:
                origin = self._database_service.get_optional_verification_entry(
                    session, request.origin_entry_uid
                )
                if origin is None or origin.round.batch_uid != batch.uid:
                    raise NotFoundError(
                        f"Entry {request.origin_entry_uid} not found in batch "
                        f"{batch.uid}."
                    )
            undrawn = self._database_service.get_undrawn_unit_uids(
                session, unit_schema, batch.uid, request.population
            )
            if len(undrawn) == 0:
                raise NotAllowedActionError(
                    "There is nothing left to draw: every unit it could draw from "
                    "has been drawn already."
                )
            if request.size is not None:
                size = request.size
            elif request.fraction is not None:
                size = math.ceil(request.fraction * len(undrawn))
            else:
                size = policy.suggested_size(len(undrawn))
            size = min(len(undrawn), max(policy.minimum_size, size))
            # The seed is secret until drawn and never chosen by the caller, so
            # the draw cannot be steered. It is recorded so the draw can be
            # replayed from the same units afterwards.
            seed = secrets.randbits(31)
            drawn = random.Random(seed).sample(undrawn, size)  # noqa: S311
            population = (
                request.population
                if request.population is not None
                and not request.population.is_whole_batch
                else None
            )
            verification_round = self._database_service.add_verification_round(
                session,
                batch_uid=batch.uid,
                seed=seed,
                requested_size=request.size,
                requested_fraction=request.fraction,
                population=population,
                population_size=len(undrawn),
                origin_entry_uid=request.origin_entry_uid,
                unit_uids=drawn,
            )
            try:
                session.flush()
            except IntegrityError as exception:
                # A unit is drawn once, which the database holds to when two
                # draws on the batch read what was left at the same time.
                raise NotAllowedActionError(
                    "Another draw took some of the same units at the same time. "
                    "Draw again."
                ) from exception
            number = len(
                self._database_service.get_verification_rounds(session, batch.uid)
            )
            self._logger.info(
                f"Drew {size} of {len(undrawn)} units of batch {batch.uid} to "
                f"verify, with seed {seed}."
            )
            return self._round_model(verification_round, number, policy)

    def decide(
        self,
        entry_uid: UUID,
        decision: VerificationDecision,
        session: Session | None = None,
    ) -> VerificationEntry:
        """Pass or fail a drawn unit.

        Failing raises an issue on the unit with the reason, flagging it for
        review, and keeps when it first failed. Passing settles what verifying
        raised on it, so a unit failed, fixed and passed again leaves the
        review queue with it.

        Parameters
        ----------
        entry_uid: UUID
            The entry of the unit decided on.
        decision: VerificationDecision
            Whether it passes, and why not where it fails.
        session: Session | None
            Session to decide in.

        Returns
        -------
        VerificationEntry
            The entry as it now stands.

        Raises
        ------
        NotFoundError
            There is no such entry.
        NotAllowedActionError
            The batch cannot be verified now, or the unit has been taken out of
            the project and there is nothing left of it to check.
        """
        with self._database_service.get_session(session) as session:
            entry = self._database_service.get_optional_verification_entry(
                session, entry_uid
            )
            if entry is None:
                raise NotFoundError(f"Entry {entry_uid} not found.")
            self._assert_can_verify(entry.round.batch, session)
            unit = entry.unit
            if not unit.selected:
                raise NotAllowedActionError(
                    f"{unit.identifier} has been taken out of the project, and is "
                    "not verified."
                )
            now = datetime.now()
            entry.verdict = decision.verdict
            entry.decided_at = now
            # Whatever verifying raised before is answered by this decision.
            # Failing again raises it anew, so one is open at a time, saying
            # what is wrong now.
            self._review_service.settle_raised_by(
                unit.uid, ReviewIssueSource.VERIFICATION, session=session
            )
            if decision.verdict == VerificationVerdict.FAILED:
                reason = (decision.reason or "").strip()
                entry.reason = reason
                if entry.failed_at is None:
                    entry.failed_at = now
                self._review_service.raise_issue(
                    unit.uid,
                    f"{FAILED_VERIFICATION}{reason}",
                    ReviewIssueSource.VERIFICATION,
                    session=session,
                )
            session.flush()
            rounds = self._database_service.get_verification_rounds(
                session, entry.round.batch_uid
            )
            number = next(
                number
                for number, verification_round in enumerate(rounds, start=1)
                if verification_round.uid == entry.round_uid
            )
            return self._entry_model(entry, number)

    def blocking(
        self, batch: DatabaseBatch, session: Session | None = None
    ) -> list[str]:
        """Why verifying holds a batch back from being completed.

        Parameters
        ----------
        batch: DatabaseBatch
            The batch about to be completed.
        session: Session | None
            Session to look in.

        Returns
        -------
        list[str]
            One line per kind of reason. Empty where nothing holds it back,
            which includes a batch whose root verifies nothing.
        """
        with self._database_service.get_session(session) as session:
            found = self._policy_of(batch, session)
            if found is None:
                return []
            policy, unit_schema = found
            rounds = self._database_service.get_verification_rounds(session, batch.uid)
            population_size = self._database_service.get_item_count(
                session, unit_schema, batch=batch.uid, selected=True
            )
            return self._blocking(policy, population_size, self._entry_models(rounds))

    def _get_batch(self, session: Session, batch_uid: UUID) -> DatabaseBatch:
        batch = self._database_service.get_optional_batch(session, batch_uid)
        if batch is None:
            raise NotFoundError(f"Batch {batch_uid} not found.")
        return batch

    def _policy_of(
        self, batch: DatabaseBatch, session: Session
    ) -> tuple[VerificationPolicy, ItemSchema] | None:
        """The policy the root of the batch's project verifies with, and the
        schema of what it verifies. None where it verifies nothing."""
        root = self._schema_service.root_of(batch, session)
        unit = root.review_unit
        if unit is None or unit.verification is None:
            return None
        unit_schema = root.items.get(unit.schema_uid)
        if unit_schema is None:
            return None
        return unit.verification, unit_schema

    def _assert_can_verify(
        self, batch: DatabaseBatch, session: Session
    ) -> tuple[VerificationPolicy, ItemSchema]:
        """Refuse to draw or decide where the batch is not there to verify:
        not verified at all, still processing its images, or completed."""
        self._schema_service.assert_can_change(batch, session)
        found = self._policy_of(batch, session)
        if found is None:
            raise NotAllowedActionError(
                f"Batch {batch.uid} is not verified: the schema of its project "
                "declares no verification."
            )
        if not batch.image_post_processing_complete:
            raise NotAllowedActionError(
                f"Batch {batch.uid} is verified once its images are processed and "
                f"until it is locked, and is {batch.status.name}."
            )
        return found

    def _entry_models(
        self, rounds: Sequence[DatabaseVerificationRound]
    ) -> list[VerificationEntry]:
        """The entries of the rounds, round by round and by identifier within
        each."""
        return [
            self._entry_model(entry, number)
            for number, verification_round in enumerate(rounds, start=1)
            for entry in sorted(
                verification_round.entries,
                key=lambda entry: entry.unit.identifier,
            )
        ]

    def _entry_model(
        self, entry: DatabaseVerificationEntry, round_number: int
    ) -> VerificationEntry:
        unit = entry.unit
        return VerificationEntry(
            uid=entry.uid,
            round_uid=entry.round_uid,
            round_number=round_number,
            unit_uid=unit.uid,
            identifier=unit.identifier,
            pseudonym=unit.pseudonym,
            verdict=entry.verdict,
            state=self._state(entry),
            reason=entry.reason,
            decided_at=entry.decided_at,
            failed_at=entry.failed_at,
            last_changed=unit.last_changed,
        )

    @staticmethod
    def _state(entry: DatabaseVerificationEntry) -> VerificationState:
        """Where a drawn unit stands, first of these that holds:

        1. ``REMOVED``: the unit is out of the project, whatever was decided,
           since there is nothing left of it to check.
        2. ``PENDING``: nothing has been decided.
        3. ``NEEDS_RECHECK``: something in or under the unit changed after the
           last decision, so it was made on something that is no longer there.
        4. ``PASSED`` or ``FAILED``, as last decided.
        """
        unit = entry.unit
        if not unit.selected:
            return VerificationState.REMOVED
        if entry.verdict == VerificationVerdict.PENDING:
            return VerificationState.PENDING
        if (
            entry.decided_at is not None
            and unit.last_changed is not None
            and unit.last_changed > entry.decided_at
        ):
            return VerificationState.NEEDS_RECHECK
        if entry.verdict == VerificationVerdict.FAILED:
            return VerificationState.FAILED
        return VerificationState.PASSED

    @staticmethod
    def _round_model(
        verification_round: DatabaseVerificationRound,
        number: int,
        policy: VerificationPolicy,
    ) -> VerificationRound:
        entries = verification_round.entries
        decided = sum(1 for entry in entries if entry.decided_at is not None)
        failed = sum(1 for entry in entries if entry.failed_at is not None)
        return VerificationRound(
            uid=verification_round.uid,
            batch_uid=verification_round.batch_uid,
            number=number,
            created_at=verification_round.created_at,
            seed=verification_round.seed,
            requested_size=verification_round.requested_size,
            requested_fraction=verification_round.requested_fraction,
            population=verification_round.population,
            population_size=verification_round.population_size,
            origin_entry_uid=verification_round.origin_entry_uid,
            drawn=len(entries),
            decided=decided,
            failed=failed,
            failure_rate_exceeded=(
                policy.failure_rate_warning is not None
                and decided > 0
                and failed / decided > policy.failure_rate_warning
            ),
        )

    def _blocking(
        self,
        policy: VerificationPolicy,
        population_size: int,
        entries: Sequence[VerificationEntry],
    ) -> list[str]:
        """Why the batch cannot be completed yet, one line per kind of reason.

        A unit failed and not passed since blocks whether or not verifying is
        required: what was found wrong is answered before the batch is locked.
        Where it is required, the batch also needs at least the policy's
        minimum of units drawn that are still in the project, or every unit
        where it holds fewer, each decided on as it now stands. Units taken out
        after they were drawn do not count towards that, so taking them out is
        answered by drawing more.

        Parameters
        ----------
        policy: VerificationPolicy
            The policy of the root of the batch's project.
        population_size: int
            How many units of the batch are in the project.
        entries: Sequence[VerificationEntry]
            Every entry of the batch's rounds.
        """
        reasons: list[str] = []
        if policy.required:
            in_project = [
                entry for entry in entries if entry.state != VerificationState.REMOVED
            ]
            needed = min(policy.minimum_size, population_size)
            if len(in_project) < needed:
                reasons.append(
                    f"Draw {needed - len(in_project)} more: {needed} of the units "
                    f"in the project are to be verified, and {len(in_project)} "
                    "have been drawn."
                )
        failed = [
            entry
            for entry in entries
            if entry.verdict == VerificationVerdict.FAILED
            and entry.state != VerificationState.REMOVED
        ]
        if failed:
            reasons.append(
                f"{self._named(failed)} failed verification. Fix and pass them "
                "again, or take them out of the project."
            )
        if policy.required:
            pending = [
                entry for entry in entries if entry.state == VerificationState.PENDING
            ]
            if pending:
                reasons.append(f"{self._named(pending)} not verified yet.")
            changed = [
                entry
                for entry in entries
                if entry.state == VerificationState.NEEDS_RECHECK
                and entry.verdict == VerificationVerdict.PASSED
            ]
            if changed:
                reasons.append(
                    f"{self._named(changed)} changed since they were verified."
                )
        return reasons

    @classmethod
    def _named(cls, entries: Sequence[VerificationEntry]) -> str:
        """How many units, naming the first few."""
        shown = ", ".join(entry.identifier for entry in entries[: cls._NAMED_UNITS])
        rest = len(entries) - cls._NAMED_UNITS
        named = f"{shown} and {rest} more" if rest > 0 else shown
        noun = "unit" if len(entries) == 1 else "units"
        return f"{len(entries)} {noun} ({named})"
