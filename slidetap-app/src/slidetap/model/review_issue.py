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

"""Something raised as wrong with an item, on the unit it is under."""

from datetime import datetime
from uuid import UUID

from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.review_issue_source import ReviewIssueSource


class ReviewIssue(CamelCaseBaseModel):
    """Something wrong with an item, and the review unit it is settled on.

    Raised on any item, by a user or by an importer, and answered on the review
    unit above it, which is flagged for it. An item can have several open at
    once, each settled on its own.
    """

    uid: UUID
    item_uid: UUID
    """The item the issue is about."""

    item_identifier: str
    """What names the item where an issue is listed."""

    item_schema_uid: UUID
    """Which kind it is, since a list of these holds several kinds of item."""

    review_unit_uid: UUID
    """The unit it is answered on, and the one that is flagged for it."""

    reason: str
    source: ReviewIssueSource
    """What kind of thing raised it. Which one is not recorded."""

    raised_at: datetime

    resolved_at: datetime | None = None
    """When it was settled, empty while it is still open."""
