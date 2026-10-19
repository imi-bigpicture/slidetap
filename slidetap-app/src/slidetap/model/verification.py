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

"""Verifying a batch: checking a random sample of its review units by hand."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field, model_validator

from slidetap.model.base_model import CamelCaseBaseModel, FrozenBaseModel
from slidetap.model.schema.verification_policy import VerificationSuggestion
from slidetap.model.table import AttributeFilter, RelationFilter

FAILED_VERIFICATION = "Failed verification: "
"""What the issue a failed unit raises says before the verifier's reason."""


class VerificationVerdict(Enum):
    """What the verifier last decided about a drawn unit."""

    PENDING = "pending"
    """Drawn and not looked at yet."""
    PASSED = "passed"
    FAILED = "failed"


class VerificationState(Enum):
    """Where a drawn unit stands, read from its verdict and from what has
    happened to the unit since.

    Derived rather than stored: a unit taken out of the project, or edited
    after it was decided on, is so because of what was done to the unit, and a
    stored state would have to be kept up with every way of doing it.
    """

    PENDING = "pending"
    """Not decided on yet."""
    PASSED = "passed"
    FAILED = "failed"
    """Failed, and neither checked again nor taken out of the project since."""
    NEEDS_RECHECK = "needs_recheck"
    """Decided on, and something under it was saved afterwards, so what was
    decided on is not what is there now."""
    REMOVED = "removed"
    """Taken out of the project after it was drawn. What it says about the
    batch still counts, but there is nothing left to check."""


class VerificationPopulation(FrozenBaseModel):
    """Which units of the batch a round is drawn from, as the item tables
    filter them.

    Empty is every unit of the batch. Units taken out of the project, and units
    already drawn by an earlier round, are left out whatever this says.
    """

    attribute_filters: list[AttributeFilter] | None = None
    relation_filters: list[RelationFilter] | None = None

    @property
    def is_whole_batch(self) -> bool:
        return not self.attribute_filters and not self.relation_filters


class VerificationRoundCreate(CamelCaseBaseModel):
    """A draw of units of a batch to verify.

    How many as a count or as a share of the units it is drawn from, and the
    policy's suggestion where neither is given.
    """

    size: int | None = Field(default=None, ge=1)
    fraction: float | None = Field(default=None, gt=0, le=1)
    population: VerificationPopulation | None = None
    origin_entry_uid: UUID | None = None
    """The drawn unit whose failure this round follows up on, where it does."""

    @model_validator(mode="after")
    def _size_or_fraction(self) -> "VerificationRoundCreate":
        if self.size is not None and self.fraction is not None:
            raise ValueError("A draw is given a size or a fraction, not both.")
        return self


class VerificationRound(CamelCaseBaseModel):
    """One draw of units of a batch to verify, and how it is going."""

    uid: UUID
    batch_uid: UUID
    number: int
    """Its place among the rounds of the batch, from one."""
    created_at: datetime
    seed: int
    """The random seed it was drawn with, picked by the server and never by
    the verifier, so that a draw cannot be steered. With the units it was drawn
    from, ordered by identifier, it tells which units it drew."""
    requested_size: int | None = None
    """How many were asked for. None where a fraction was, or where nothing
    was and the policy's suggestion was drawn."""
    requested_fraction: float | None = None
    """What share was asked for. None where a size was, or nothing."""
    population: VerificationPopulation | None = None
    """How the units it was drawn from were filtered. None for every unit in
    the project no earlier round had drawn."""
    population_size: int
    """How many units it was drawn from."""
    origin_entry_uid: UUID | None = None
    """The entry whose failure the round follows up on, where it does."""
    drawn: int
    """How many units it drew."""
    decided: int
    """How many of those have been decided on at least once."""
    failed: int
    """How many of those failed at least once, fixed since or not: what a round
    says about the batch is what was found, not what was done about it."""
    failure_rate_exceeded: bool = False
    """Whether more failed than the policy warns at."""


class VerificationEntry(CamelCaseBaseModel):
    """A unit drawn for verification, and where it stands.

    Both what was decided, ``verdict``, and where that leaves the unit now,
    ``state``: a unit passed and changed since is still passed, but needs
    checking again.
    """

    uid: UUID
    round_uid: UUID
    round_number: int
    """The `VerificationRound.number` of the round that drew it."""
    unit_uid: UUID
    """The review unit drawn."""
    identifier: str
    pseudonym: str | None = None
    verdict: VerificationVerdict
    """What was last decided, as it was decided."""
    state: VerificationState
    """Where the unit stands now, from the verdict and what has happened to
    the unit since."""
    reason: str | None = None
    """Why it failed, kept after it passes again."""
    decided_at: datetime | None = None
    """When it was last decided on, passed or failed. None while pending."""
    failed_at: datetime | None = None
    """When it first failed. Kept after it passes again, which is what tells a
    fixed unit from one that passed the first time."""
    last_changed: datetime | None = None
    """When anything in or under the unit last changed."""


class VerificationDecision(CamelCaseBaseModel):
    """What a verifier decided about a drawn unit."""

    verdict: VerificationVerdict
    reason: str | None = Field(default=None, max_length=512 - len(FAILED_VERIFICATION))
    """Why it failed. Required to fail it, and not used to pass it. As long as
    fits in the issue it raises, after what the issue says before it."""

    @model_validator(mode="after")
    def _failing_says_why(self) -> "VerificationDecision":
        if self.verdict == VerificationVerdict.PENDING:
            raise ValueError("A decision passes or fails.")
        if self.verdict == VerificationVerdict.FAILED and not (
            self.reason and self.reason.strip()
        ):
            raise ValueError("Failing a unit needs a reason.")
        return self


class BatchVerification(CamelCaseBaseModel):
    """How verifying a batch stands: what was drawn, what was decided, and
    whether it holds the batch back from being completed."""

    batch_uid: UUID
    verified: bool
    """Whether the batch is verified at all. False where the root of its project
    declares no verification policy, which leaves the rest empty."""
    required: bool = False
    population_size: int = 0
    """How many units of the batch are in the project."""
    undrawn: int = 0
    """How many of those no round has drawn yet."""
    suggestion: VerificationSuggestion | None = None
    """How many a whole-batch draw would take of what is undrawn, as the policy
    suggests, and why. None where the batch is not verified."""
    rounds: list[VerificationRound] = Field(default_factory=list)
    """In the order they were drawn."""
    entries: list[VerificationEntry] = Field(default_factory=list)
    """Of every round, round by round and by identifier within each."""
    blocking: list[str] = Field(default_factory=list)
    """Why the batch cannot be completed yet, as far as verifying goes. Empty
    when it can."""
