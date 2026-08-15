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

"""Something found wrong with an item, raised on the unit above it."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slidetap.database.db import Base
from slidetap.database.item import DatabaseItem
from slidetap.model.review_issue import ReviewIssue
from slidetap.model.review_issue_source import ReviewIssueSource


class DatabaseReviewIssue(Base):
    """Something raised as wrong with an item.

    Held here rather than on the item, since an item can have more than one
    open at once, each raised on its own and settled on its own.
    """

    __tablename__ = "review_issue"

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    item_uid: Mapped[UUID] = mapped_column(ForeignKey("item.uid"), index=True)
    """The item the issue is about."""

    review_unit_uid: Mapped[UUID] = mapped_column(ForeignKey("item.uid"), index=True)
    """The unit it is answered on. Written down rather than walked up to when
    asked for, so that listing what is open on a case is one query, and so that
    an item moved to another parent keeps its issue where it was raised."""

    reason: Mapped[str] = mapped_column(String(512))
    source: Mapped[ReviewIssueSource] = mapped_column(Enum(ReviewIssueSource))
    raised_at: Mapped[datetime] = mapped_column(DateTime)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    item: Mapped[DatabaseItem[Any]] = relationship(
        DatabaseItem,
        foreign_keys=[item_uid],
        lazy="joined",
    )

    @property
    def model(self) -> ReviewIssue:
        return ReviewIssue(
            uid=self.uid,
            item_uid=self.item_uid,
            item_identifier=self.item.identifier,
            item_schema_uid=self.item.schema_uid,
            review_unit_uid=self.review_unit_uid,
            reason=self.reason,
            source=self.source,
            raised_at=self.raised_at,
            resolved_at=self.resolved_at,
        )
