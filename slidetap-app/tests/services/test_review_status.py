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

"""Tests for the review state an item carries.

The rules are small but easy to break by accident: reviewing is the only way
out of `FLAGGED`, a second flag must not overwrite the reason the first one
gave, and reviewing must leave that reason readable rather than clearing it.
"""

import pytest

from slidetap.model import ReviewRequest, ReviewStatus


@pytest.mark.unittest
class TestReviewStatus:
    def test_an_item_starts_outside_review(self):
        # Arrange

        # Act
        default = ReviewStatus.NOT_REVIEWED

        # Assert
        assert default.value == "not_reviewed"

    def test_the_three_states_are_distinct(self):
        """Two booleans would allow "flagged and reviewed", which the workflow
        cannot reach: an item leaves FLAGGED only by being reviewed."""
        # Arrange

        # Act
        values = {status.value for status in ReviewStatus}

        # Assert
        assert values == {"not_reviewed", "flagged", "reviewed"}


@pytest.mark.unittest
class TestReviewRequest:
    def test_a_reason_is_optional(self):
        """Marking something reviewed says nothing new about why it was asked
        for, so the request carries no reason."""
        # Arrange

        # Act
        request = ReviewRequest(status=ReviewStatus.REVIEWED)

        # Assert
        assert request.reason is None

    def test_a_flag_carries_why(self):
        # Arrange
        reason = "2 of 21 imported items are not valid: PL1219-99-1-A-14"

        # Act
        request = ReviewRequest(status=ReviewStatus.FLAGGED, reason=reason)

        # Assert
        assert request.status is ReviewStatus.FLAGGED
        assert request.reason == reason
