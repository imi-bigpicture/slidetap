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

"""Service for the per-unit metadata search-item rows."""

from datetime import datetime, timezone
from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from slidetap.database import DatabaseMetadataSearchItem
from slidetap.model import MetadataImportStatus, MetadataSearchItem
from slidetap.services.database_service import DatabaseService


class MetadataSearchItemService:
    """CRUD for the metadata_search_item table."""

    def __init__(self, database_service: DatabaseService) -> None:
        self._database_service = database_service

    def create(
        self,
        batch_uid: UUID,
        identifier: str,
        schema_uid: UUID,
        session: Optional[Session] = None,
    ) -> DatabaseMetadataSearchItem:
        """Create a new search item in NOT_STARTED state."""
        with self._database_service.get_session(session) as session:
            item = DatabaseMetadataSearchItem(
                batch_uid=batch_uid,
                identifier=identifier,
                schema_uid=schema_uid,
                status=MetadataImportStatus.NOT_STARTED,
                attempted_at=datetime.now(timezone.utc),
            )
            session.add(item)
            session.flush()
            return item

    def mark_complete(
        self,
        target: Union[UUID, DatabaseMetadataSearchItem],
        item_uid: Optional[UUID],
        session: Optional[Session] = None,
    ) -> None:
        with self._database_service.get_session(session) as session:
            item = self._resolve(session, target)
            if item is None:
                return
            item.status = MetadataImportStatus.COMPLETE
            item.message = None
            item.item_uid = item_uid
            item.attempted_at = datetime.now(timezone.utc)

    def mark_failed(
        self,
        target: Union[UUID, DatabaseMetadataSearchItem],
        message: str,
        session: Optional[Session] = None,
    ) -> None:
        with self._database_service.get_session(session) as session:
            item = self._resolve(session, target)
            if item is None:
                return
            item.status = MetadataImportStatus.FAILED
            item.message = message
            item.item_uid = None
            item.attempted_at = datetime.now(timezone.utc)

    def reset_for_retry(
        self,
        target: Union[UUID, DatabaseMetadataSearchItem],
        session: Optional[Session] = None,
    ) -> Optional[MetadataSearchItem]:
        """Reset to NOT_STARTED + increment retry_count before queuing."""
        with self._database_service.get_session(session) as session:
            item = self._resolve(session, target)
            if item is None:
                return None
            item.status = MetadataImportStatus.NOT_STARTED
            item.message = None
            item.retry_count += 1
            item.attempted_at = datetime.now(timezone.utc)
            return item.model

    def get(self, search_item_uid: UUID) -> Optional[MetadataSearchItem]:
        with self._database_service.get_session() as session:
            item = session.get(DatabaseMetadataSearchItem, search_item_uid)
            return item.model if item is not None else None

    def list_for_batch(self, batch_uid: UUID) -> List[MetadataSearchItem]:
        with self._database_service.get_session() as session:
            query = select(DatabaseMetadataSearchItem).where(
                DatabaseMetadataSearchItem.batch_uid == batch_uid
            )
            return [item.model for item in session.scalars(query)]

    def clear_for_batch(
        self,
        batch_uid: UUID,
        session: Optional[Session] = None,
    ) -> None:
        """Delete all search items for a batch — used when starting a new search."""
        with self._database_service.get_session(session) as session:
            session.execute(
                delete(DatabaseMetadataSearchItem).where(
                    DatabaseMetadataSearchItem.batch_uid == batch_uid
                )
            )

    def delete(
        self,
        target: Union[UUID, DatabaseMetadataSearchItem],
        session: Optional[Session] = None,
    ) -> None:
        with self._database_service.get_session(session) as session:
            item = self._resolve(session, target)
            if item is not None:
                session.delete(item)

    def _resolve(
        self,
        session: Session,
        target: Union[UUID, DatabaseMetadataSearchItem],
    ) -> Optional[DatabaseMetadataSearchItem]:
        """Return the row, fetching by UID if a UID was passed in."""
        if isinstance(target, DatabaseMetadataSearchItem):
            return target
        return session.get(DatabaseMetadataSearchItem, target)
