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

"""How the review units of a batch are verified before it is completed."""

import math
from enum import Enum

from pydantic import Field, model_validator

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.schema.review_layout import ReviewLayout


class VerificationSuggestionBasis(Enum):
    """Which part of a policy a suggested draw size comes from."""

    TARGETS = "targets"
    """The smallest sample in which no failures shows the defect rate is low
    enough with the confidence asked for."""
    SIZE = "size"
    FRACTION = "fraction"
    MINIMUM = "minimum"


class VerificationSuggestion(FrozenBaseModel):
    """How many units a draw offers to take, and what that number comes from,
    so that a verifier can see why."""

    size: int
    """What is offered: ``wanted``, raised to the minimum and limited to what
    is left to draw."""
    basis: VerificationSuggestionBasis
    wanted: int
    """What the basis asks for, before the minimum and what is left to draw
    are applied."""
    undrawn: int
    """How many units are left to draw."""
    minimum_size: int
    """The fewest units a draw takes while there are that many. With a required
    policy, also what has to be drawn and decided before the batch can be
    completed; the rest of the suggestion is advice."""
    target_confidence: float | None = None
    target_defect_rate: float | None = None
    fraction: float | None = None


class VerificationPolicy(FrozenBaseModel):
    """How a sample of the review units of a batch is checked by hand before
    the batch is completed.

    Declared by the application rather than chosen in the client: what counts
    as a batch checked well enough is a decision about the dataset, and one a
    curator could loosen at will would not be a check. A new policy is a new
    root, so a project keeps the policy it was started under.
    """

    required: bool = True
    """Whether a batch must have a sample drawn and checked before it can be
    completed.

    A failed unit blocks completing either way: without this, verifying is a
    spot check somebody may make, but what they found wrong is still answered
    before the batch is locked.
    """

    default_size: int | None = Field(default=None, ge=1)
    """How many units a draw offers to take, where no fraction is given."""

    default_fraction: float | None = Field(default=None, gt=0, le=1)
    """What share of the units of the batch a draw offers to take."""

    minimum_size: int = Field(default=1, ge=1)
    """The fewest units a draw takes, whatever was asked for, unless the batch
    holds fewer."""

    target_confidence: float | None = Field(default=None, gt=0, lt=1)
    """How sure a sample without failures should leave you that the defect rate
    of the batch is at most ``target_defect_rate``."""

    target_defect_rate: float | None = Field(default=None, gt=0, lt=1)
    """The defect rate a sample without failures should rule out, with
    ``target_confidence``."""

    failure_rate_warning: float | None = Field(default=None, ge=0, le=1)
    """Share of failed units in a round above which drawing more is suggested.

    A warning rather than a block: each failed unit blocks on its own, and how
    much more to look at after a bad round is for the verifier to judge.
    """

    layout: ReviewLayout | None = None
    """What the verifier is shown of a unit. The review layout where None."""

    @model_validator(mode="after")
    def _targets_go_together(self) -> "VerificationPolicy":
        if (self.target_confidence is None) != (self.target_defect_rate is None):
            raise ValueError(
                "target_confidence and target_defect_rate are given together or "
                "not at all."
            )
        return self

    def suggested_size(self, population: int) -> int:
        """How many of ``population`` units a draw offers to take, as
        :py:meth:`suggestion` works it out."""
        return self.suggestion(population).size

    def suggestion(self, population: int) -> VerificationSuggestion:
        """How many of ``population`` units a draw offers to take, and why.

        From the targets where they are given: the smallest sample in which
        finding no failures leaves ``target_confidence`` that the defect rate
        is at most ``target_defect_rate``, ``ln(1 - c) / ln(1 - p)``. Otherwise
        from the default size or fraction, and otherwise the minimum. Never more
        than there are, nor less than the minimum while there are that many.
        """
        population = max(population, 0)
        if self.target_confidence is not None and self.target_defect_rate is not None:
            basis = VerificationSuggestionBasis.TARGETS
            wanted = math.ceil(
                math.log(1 - self.target_confidence)
                / math.log(1 - self.target_defect_rate)
            )
        elif self.default_size is not None:
            basis = VerificationSuggestionBasis.SIZE
            wanted = self.default_size
        elif self.default_fraction is not None:
            basis = VerificationSuggestionBasis.FRACTION
            wanted = math.ceil(self.default_fraction * population)
        else:
            basis = VerificationSuggestionBasis.MINIMUM
            wanted = self.minimum_size
        return VerificationSuggestion(
            size=min(population, max(self.minimum_size, wanted)),
            basis=basis,
            wanted=wanted,
            undrawn=population,
            minimum_size=self.minimum_size,
            target_confidence=self.target_confidence,
            target_defect_rate=self.target_defect_rate,
            fraction=self.default_fraction,
        )
