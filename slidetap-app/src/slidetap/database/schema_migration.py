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

"""The migration of a project to another root schema, and its issues."""

from __future__ import annotations

import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slidetap.database.db import Base
from slidetap.database.types import attribute_db_type
from slidetap.model import (
    AnyAttribute,
    MigrationObjectKind,
    MigrationState,
    ProjectStatus,
)


class StoredDroppedAttribute(BaseModel):
    """An attribute with a value that the migration left out, with the object
    it was of."""

    object_uid: UUID
    object_kind: MigrationObjectKind
    object_schema_uid: UUID
    """The schema of the target root the object is migrated to."""

    tag: str
    display_name: str
    display_value: str | None = None


class DatabaseSchemaMigration(Base):
    """The migration of a project, from it is started until it is completed
    or aborted."""

    __tablename__ = "schema_migration"

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_uid: Mapped[UUID] = mapped_column(
        ForeignKey("project.uid", ondelete="CASCADE"), unique=True
    )
    source_root_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    target_root_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    previous_status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=32)
    )
    state: Mapped[MigrationState] = mapped_column(
        Enum(MigrationState, native_enum=False, length=32)
    )
    error: Mapped[str | None] = mapped_column(Text)
    dropped: Mapped[list | None] = mapped_column(JSON)
    """The attributes dropped, as `StoredDroppedAttribute`s, once planned."""

    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    updated: Mapped[datetime.datetime] = mapped_column(DateTime)

    issues: Mapped[list[DatabaseSchemaMigrationIssue]] = relationship(
        "DatabaseSchemaMigrationIssue",
        back_populates="migration",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        project_uid: UUID,
        source_root_schema_uid: UUID,
        target_root_schema_uid: UUID,
        previous_status: ProjectStatus,
    ):
        now = datetime.datetime.now()
        super().__init__(
            uid=uuid4(),
            project_uid=project_uid,
            source_root_schema_uid=source_root_schema_uid,
            target_root_schema_uid=target_root_schema_uid,
            previous_status=previous_status,
            state=MigrationState.PLANNING,
            created=now,
            updated=now,
        )

    def set_state(self, state: MigrationState, error: str | None = None) -> None:
        self.state = state
        self.error = error
        self.updated = datetime.datetime.now()

    @property
    def dropped_attributes(self) -> list[StoredDroppedAttribute]:
        return [
            StoredDroppedAttribute.model_validate(dropped)
            for dropped in self.dropped or []
        ]

    @dropped_attributes.setter
    def dropped_attributes(self, value: list[StoredDroppedAttribute]) -> None:
        self.dropped = [dropped.model_dump(mode="json") for dropped in value]


class DatabaseSchemaMigrationIssue(Base):
    """A top-level attribute of the target schema of an object that the
    migration could not convert, and what the curator decided."""

    __tablename__ = "schema_migration_issue"
    __table_args__ = (UniqueConstraint("migration_uid", "object_uid", "tag"),)

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_uid: Mapped[UUID] = mapped_column(
        ForeignKey("schema_migration.uid", ondelete="CASCADE"), index=True
    )
    object_uid: Mapped[UUID] = mapped_column(Uuid)
    object_kind: Mapped[MigrationObjectKind] = mapped_column(
        Enum(MigrationObjectKind, native_enum=False, length=32)
    )
    object_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    """The schema of the target root the object is migrated to."""

    tag: Mapped[str] = mapped_column(String(128))
    """The tag in the target schema."""

    original: Mapped[AnyAttribute] = mapped_column(attribute_db_type)
    proposed: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    reason: Mapped[str] = mapped_column(Text)
    decision: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    decided: Mapped[bool] = mapped_column(Boolean, default=False)
    left_empty: Mapped[bool] = mapped_column(Boolean, default=False)

    migration: Mapped[DatabaseSchemaMigration] = relationship(
        DatabaseSchemaMigration, back_populates="issues"
    )

    def __init__(
        self,
        object_uid: UUID,
        object_kind: MigrationObjectKind,
        object_schema_uid: UUID,
        tag: str,
        original: AnyAttribute,
        proposed: AnyAttribute | None,
        reason: str,
    ):
        super().__init__(
            uid=uuid4(),
            object_uid=object_uid,
            object_kind=object_kind,
            object_schema_uid=object_schema_uid,
            tag=tag,
            original=original,
            proposed=proposed,
            reason=reason,
            decided=False,
            left_empty=False,
        )

    def decide(self, attribute: AnyAttribute | None) -> None:
        """Decide the value, None to leave it empty."""
        self.decision = attribute
        self.decided = True
        self.left_empty = attribute is None
