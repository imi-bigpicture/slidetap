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

"""Putting derived tables right when something has written around them."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseBatch,
    DatabaseItem,
    DatabaseUnmappedValue,
)
from slidetap.services.database_service import DatabaseService


class RepairService:
    """Checks and remakes what is derived from something else.

    Nothing here is needed to run the application: a derived table is written
    as its source is written, and this exists for when that has not happened
    --- something writing attributes by a path that does not record what they
    carry. Reached through ``slidetap-db``, which needs no model to run it.
    """

    def __init__(self, database_service: DatabaseService):
        self._database_service = database_service

    def rebuild_unmapped_values(
        self,
        project_uid: UUID | None = None,
        batch_uid: UUID | None = None,
        session: Session | None = None,
    ) -> int:
        """Read the unmapped values again from the attributes themselves.

        The repair for a table that is only ever derived: what it says is
        replaced by what the attributes say now. Returns how many values were
        written.
        """
        with self._database_service.get_session(session) as session:
            written = 0
            for attribute in session.scalars(
                self._attributes_in(project_uid, batch_uid)
            ):
                self._database_service.record_unmapped_values(attribute, session)
                written += len(list(self._database_service.unmapped_under(attribute)))
            return written

    def verify_unmapped_values(
        self,
        project_uid: UUID | None = None,
        batch_uid: UUID | None = None,
        session: Session | None = None,
    ) -> list[str]:
        """What the table says that the attributes do not, and the other way.

        Says what is wrong without changing anything, so that a rebuild can be
        a decision rather than a habit: a table that has drifted is worth
        knowing about, since it means something wrote attributes by a path that
        does not record what they carry.
        """
        with self._database_service.get_session(session) as session:
            differences: list[str] = []
            for attribute in session.scalars(
                self._attributes_in(project_uid, batch_uid)
            ):
                expected = set(self._database_service.unmapped_under(attribute))
                recorded = {
                    (row.uid, row.schema_uid, row.value)
                    for row in session.scalars(
                        select(DatabaseUnmappedValue).where(
                            DatabaseUnmappedValue.root_attribute_uid == attribute.uid
                        )
                    )
                }
                for missing in sorted(expected - recorded, key=str):
                    differences.append(f"{attribute.uid}: not recorded {missing}")
                for extra in sorted(recorded - expected, key=str):
                    differences.append(
                        f"{attribute.uid}: recorded but no longer there {extra}"
                    )
            return differences

    @staticmethod
    def _attributes_in(project_uid: UUID | None, batch_uid: UUID | None):
        """The attribute rows of a project, of a batch, or of everything."""
        query = select(DatabaseAttribute).where(
            DatabaseAttribute.attribute_item_uid.is_not(None)
        )
        if batch_uid is not None:
            return query.join(
                DatabaseItem, DatabaseItem.uid == DatabaseAttribute.attribute_item_uid
            ).where(DatabaseItem.batch_uid == batch_uid)
        if project_uid is not None:
            return (
                query.join(
                    DatabaseItem,
                    DatabaseItem.uid == DatabaseAttribute.attribute_item_uid,
                )
                .join(DatabaseBatch, DatabaseBatch.uid == DatabaseItem.batch_uid)
                .where(DatabaseBatch.project_uid == project_uid)
            )
        return query
