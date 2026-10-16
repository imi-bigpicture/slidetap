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

"""Per-unit metadata-import attempt rows.

These live in their own table — not the item table — so the item table
contains only complete real items. Failed search items have no item_uid;
successful ones link to the entry-level item that was created. When the
linked item is removed via curate, the search item is cascade-deleted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import Base
from slidetap.model import MetadataImportStatus, MetadataSearchItem


class DatabaseMetadataSearchItem(Base):
    __tablename__ = "metadata_search_item"

    MESSAGE_LENGTH: ClassVar[int] = 512
    TRUNCATION_MARKER: ClassVar[str] = "… [truncated]"

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    batch_uid: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("batch.uid", ondelete="CASCADE"), index=True
    )
    identifier: Mapped[str] = mapped_column(String(128))
    schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)
    status: Mapped[MetadataImportStatus] = mapped_column(Enum(MetadataImportStatus))
    message: Mapped[str | None] = mapped_column(String(MESSAGE_LENGTH))
    item_uid: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("item.uid", ondelete="CASCADE"), index=True
    )
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    search_parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    """What the importer imported this unit from."""

    def __init__(
        self,
        batch_uid: UUID,
        identifier: str,
        schema_uid: UUID,
        status: MetadataImportStatus = MetadataImportStatus.NOT_STARTED,
        message: str | None = None,
        item_uid: UUID | None = None,
        attempted_at: datetime | None = None,
        retry_count: int = 0,
        search_parameters: dict[str, Any] | None = None,
        uid: UUID | None = None,
    ):
        super().__init__(
            uid=uid if (uid and uid != UUID(int=0)) else uuid4(),
            batch_uid=batch_uid,
            identifier=identifier,
            schema_uid=schema_uid,
            status=status,
            message=self.fitted_message(message),
            item_uid=item_uid,
            attempted_at=attempted_at,
            retry_count=retry_count,
            search_parameters=search_parameters,
        )

    @classmethod
    def fitted_message(cls, message: str | None) -> str | None:
        """The message cut to the width of the column.

        Exception text recorded on a failure can be longer than the column,
        which Postgres refuses, so recording the failure would fail too. The
        leading characters, where the cause is, are kept and the cut marked.
        """
        if message is None or len(message) <= cls.MESSAGE_LENGTH:
            return message
        kept_length = cls.MESSAGE_LENGTH - len(cls.TRUNCATION_MARKER)
        return message[:kept_length] + cls.TRUNCATION_MARKER

    @property
    def model(self) -> MetadataSearchItem:
        return MetadataSearchItem(
            uid=self.uid,
            batch_uid=self.batch_uid,
            identifier=self.identifier,
            schema_uid=self.schema_uid,
            status=self.status,
            message=self.message,
            item_uid=self.item_uid,
            attempted_at=self.attempted_at,
            retry_count=self.retry_count,
            search_parameters=self.search_parameters,
        )
