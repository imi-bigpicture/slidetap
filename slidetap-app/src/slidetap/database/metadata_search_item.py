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
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import Base
from slidetap.model import MetadataImportStatus, MetadataSearchItem


class DatabaseMetadataSearchItem(Base):
    __tablename__ = "metadata_search_item"

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    batch_uid: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("batch.uid", ondelete="CASCADE"), index=True
    )
    identifier: Mapped[str] = mapped_column(String(128))
    schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)
    status: Mapped[MetadataImportStatus] = mapped_column(Enum(MetadataImportStatus))
    message: Mapped[Optional[str]] = mapped_column(String(512))
    item_uid: Mapped[Optional[UUID]] = mapped_column(
        Uuid, ForeignKey("item.uid", ondelete="CASCADE")
    )
    attempted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    def __init__(
        self,
        batch_uid: UUID,
        identifier: str,
        schema_uid: UUID,
        status: MetadataImportStatus = MetadataImportStatus.NOT_STARTED,
        message: Optional[str] = None,
        item_uid: Optional[UUID] = None,
        attempted_at: Optional[datetime] = None,
        retry_count: int = 0,
        uid: Optional[UUID] = None,
    ):
        super().__init__(
            uid=uid if (uid and uid != UUID(int=0)) else uuid4(),
            batch_uid=batch_uid,
            identifier=identifier,
            schema_uid=schema_uid,
            status=status,
            message=message,
            item_uid=item_uid,
            attempted_at=attempted_at,
            retry_count=retry_count,
        )

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
        )
