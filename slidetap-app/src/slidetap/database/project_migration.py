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

"""The migration of a project to another root schema, its attribute issues,
and its dropped attributes."""

import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slidetap.database.db import Base
from slidetap.database.types import attribute_db_type
from slidetap.model import AnyAttribute, MigrationState, ProjectStatus


class DatabaseMigrationAttributeIssue(Base):
    """A top-level attribute of the target schema of an object that the
    migration could not convert or left invalid, and what the curator
    decided."""

    __tablename__ = "migration_attribute_issue"
    __table_args__ = (
        UniqueConstraint("migration_uid", "item_uid", "attribute_schema_uid"),
    )

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_uid: Mapped[UUID] = mapped_column(
        ForeignKey("project_migration.uid", ondelete="CASCADE"), index=True
    )
    item_uid: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("item.uid", ondelete="CASCADE")
    )
    """The item, or None for the project or the dataset of the migration."""

    object_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    """The schema of the target root the object is migrated to."""

    attribute_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    """The attribute schema in the target root the decision is on."""

    original: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    """The attribute of the source object, or None where it had none."""

    proposed: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    """What could be converted, for the curator to start from, or None."""

    reason: Mapped[str] = mapped_column(Text)
    """Why the attribute was not converted."""

    decision: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    """The decided value, None where undecided or left empty."""

    decided: Mapped[bool] = mapped_column(Boolean, default=False)
    """Whether the curator decided the attribute issue."""

    def __init__(
        self,
        item_uid: UUID | None,
        object_schema_uid: UUID,
        attribute_schema_uid: UUID,
        original: AnyAttribute | None,
        proposed: AnyAttribute | None,
        reason: str,
    ):
        """Create an undecided attribute issue.

        Parameters
        ----------
        item_uid: UUID | None
            The item, or None for the project or the dataset.
        object_schema_uid: UUID
            The target schema of the object.
        attribute_schema_uid: UUID
            The attribute schema of the target tag.
        original: AnyAttribute | None
            The attribute of the source object, or None where it had none.
        proposed: AnyAttribute | None
            What could be converted, or None.
        reason: str
            Why the attribute was not converted.
        """
        super().__init__(
            uid=uuid4(),
            item_uid=item_uid,
            object_schema_uid=object_schema_uid,
            attribute_schema_uid=attribute_schema_uid,
            original=original,
            proposed=proposed,
            reason=reason,
            decided=False,
        )

    def set_decision(self, attribute: AnyAttribute | None) -> None:
        """Decide the attribute issue.

        Parameters
        ----------
        attribute: AnyAttribute | None
            The value, on the attribute schema of the attribute issue, or None
            to leave the attribute empty.
        """
        self.decision = attribute
        self.decided = True


class DatabaseMigrationDroppedAttribute(Base):
    """An attribute with a value of an object that the migration left out, as
    it has no target."""

    __tablename__ = "migration_dropped_attribute"

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_uid: Mapped[UUID] = mapped_column(
        ForeignKey("project_migration.uid", ondelete="CASCADE"), index=True
    )
    item_uid: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("item.uid", ondelete="CASCADE")
    )
    """The item, or None for the project or the dataset of the migration."""

    object_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    """The schema of the target root the object is migrated to."""

    attribute_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    """The attribute schema in the source root."""

    original: Mapped[AnyAttribute] = mapped_column(attribute_db_type)
    """The attribute of the source object."""

    def __init__(
        self,
        item_uid: UUID | None,
        object_schema_uid: UUID,
        attribute_schema_uid: UUID,
        original: AnyAttribute,
    ):
        """Create a dropped attribute.

        Parameters
        ----------
        item_uid: UUID | None
            The item, or None for the project or the dataset.
        object_schema_uid: UUID
            The target schema of the object.
        attribute_schema_uid: UUID
            The source attribute schema of the attribute.
        original: AnyAttribute
            The attribute of the source object.
        """
        super().__init__(
            uid=uuid4(),
            item_uid=item_uid,
            object_schema_uid=object_schema_uid,
            attribute_schema_uid=attribute_schema_uid,
            original=original,
        )


class DatabaseProjectMigration(Base):
    """The migration of a project, from it is created until it is completed
    or reverted."""

    __tablename__ = "project_migration"

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_uid: Mapped[UUID] = mapped_column(
        ForeignKey("project.uid", ondelete="CASCADE"), unique=True
    )
    source_root_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    """The root the project is on."""

    target_root_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    """The root the project is migrated to."""

    previous_status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=32)
    )
    """The status the project had, which it gets back."""

    state: Mapped[MigrationState] = mapped_column(
        Enum(MigrationState, native_enum=False, length=32)
    )
    error: Mapped[str | None] = mapped_column(Text)
    """Why planning or completing failed."""

    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    updated: Mapped[datetime.datetime] = mapped_column(DateTime)

    attribute_issues: Mapped[list[DatabaseMigrationAttributeIssue]] = relationship(
        "DatabaseMigrationAttributeIssue",
        cascade="all, delete-orphan",
    )
    dropped_attributes: Mapped[list[DatabaseMigrationDroppedAttribute]] = relationship(
        "DatabaseMigrationDroppedAttribute",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        project_uid: UUID,
        source_root_schema_uid: UUID,
        target_root_schema_uid: UUID,
        previous_status: ProjectStatus,
    ):
        """Create a migration, to be planned.

        Parameters
        ----------
        project_uid: UUID
            The project.
        source_root_schema_uid: UUID
            The root the project is on.
        target_root_schema_uid: UUID
            The root the project is migrated to.
        previous_status: ProjectStatus
            The status the project has.
        """
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
        """Set the state of the migration, and when it was updated.

        Parameters
        ----------
        state: MigrationState
            The state.
        error: str | None = None
            Why planning or completing failed, or None.
        """
        self.state = state
        self.error = error
        self.updated = datetime.datetime.now()
