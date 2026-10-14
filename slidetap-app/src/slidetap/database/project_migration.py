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

"""The migration of a project to another root schema, the entities with
attribute issues, and their attribute issues."""

import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slidetap.database.db import Base
from slidetap.database.types import attribute_db_type
from slidetap.model import (
    AnyAttribute,
    AttributeMigrationIssue,
    EntityMigrationIssues,
    MigrationStatus,
    ProjectMigration,
    ProjectStatus,
)


class DatabaseAttributeMigrationIssue(Base):
    """A top-level attribute of an entity that the migration could not
    convert, left invalid, or dropped, and how the curator resolved it.

    An issue of a value the migration could not convert has both a source and
    a target attribute schema, one of an attribute the migration made invalid
    has a target attribute schema and the source one where there was one, and
    one of a dropped attribute has only a source attribute schema."""

    __tablename__ = "attribute_migration_issue"
    __table_args__ = (
        # Every issue is about a source attribute, a target attribute, or both.
        CheckConstraint(
            "source_attribute_schema_uid IS NOT NULL "
            "OR target_attribute_schema_uid IS NOT NULL",
            name="ck_attribute_migration_issue_attribute_schema",
        ),
        # One issue per target attribute of an entity.
        Index(
            "uq_attribute_migration_issue_target",
            "migration_entity_uid",
            "target_attribute_schema_uid",
            unique=True,
            sqlite_where=text("target_attribute_schema_uid IS NOT NULL"),
            postgresql_where=text("target_attribute_schema_uid IS NOT NULL"),
        ),
        # One issue per dropped source attribute of an entity.
        Index(
            "uq_attribute_migration_issue_dropped",
            "migration_entity_uid",
            "source_attribute_schema_uid",
            unique=True,
            sqlite_where=text("target_attribute_schema_uid IS NULL"),
            postgresql_where=text("target_attribute_schema_uid IS NULL"),
        ),
    )

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_entity_uid: Mapped[UUID] = mapped_column(
        ForeignKey("migration_entity.uid", ondelete="CASCADE"), index=True
    )
    """The entity the attribute belongs to."""

    source_attribute_schema_uid: Mapped[UUID | None] = mapped_column(Uuid)
    """The schema in the source root of the original attribute, or None where
    the issue has no original attribute, such as for an attribute that is new
    in the target root."""

    target_attribute_schema_uid: Mapped[UUID | None] = mapped_column(Uuid)
    """The schema of the attribute in the target root that the issue is
    resolved on, or None for a dropped attribute."""

    original: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    """The attribute of the source entity, or None where it had none."""

    proposed: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    """What could be converted, for the curator to start from, or None."""

    problem: Mapped[str] = mapped_column(Text)
    """A description, for the curator, of why the issue needs resolving: a
    value the migration could not migrate, an attribute the migration made
    invalid, or an attribute the migration dropped."""

    resolved: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    """The value the issue is resolved with, None where left empty, accepted
    as dropped, or not yet resolved."""

    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    """When the issue was resolved, None until it is."""

    def __init__(
        self,
        source_attribute_schema_uid: UUID | None,
        target_attribute_schema_uid: UUID | None,
        original: AnyAttribute | None,
        proposed: AnyAttribute | None,
        problem: str,
    ):
        """Create an unresolved attribute issue.

        Parameters
        ----------
        source_attribute_schema_uid: UUID | None
            The attribute schema of the original, or None where there is none.
        target_attribute_schema_uid: UUID | None
            The attribute schema of the target tag, or None for a dropped
            attribute.
        original: AnyAttribute | None
            The attribute of the source entity, or None where it had none.
        proposed: AnyAttribute | None
            What could be converted, or None.
        problem: str
            What needs the curator's decision.
        """
        super().__init__(
            uid=uuid4(),
            source_attribute_schema_uid=source_attribute_schema_uid,
            target_attribute_schema_uid=target_attribute_schema_uid,
            original=original,
            proposed=proposed,
            problem=problem,
            resolved_at=None,
        )

    @property
    def dropped(self) -> bool:
        """Whether the issue is of an attribute the migration dropped."""
        return self.target_attribute_schema_uid is None

    def resolve(self, attribute: AnyAttribute | None) -> None:
        """Resolve the attribute issue, or accept a dropped attribute.

        Parameters
        ----------
        attribute: AnyAttribute | None
            The value, on the attribute schema of the attribute issue, or None
            to leave the attribute empty or accept it as dropped.

        Raises
        ------
        ValueError
            If a value is given for a dropped attribute.
        """
        if self.dropped and attribute is not None:
            raise ValueError("A dropped attribute is accepted, not given a value.")
        self.resolved = attribute
        self.resolved_at = datetime.datetime.now()

    @property
    def model(self) -> AttributeMigrationIssue:
        """Make the model of the attribute issue."""
        return AttributeMigrationIssue(
            uid=self.uid,
            target_attribute_schema_uid=self.target_attribute_schema_uid,
            original=self.original,
            proposed=self.proposed,
            problem=self.problem,
            resolved=self.resolved,
            resolved_at=self.resolved_at,
        )


class DatabaseMigrationEntity(Base):
    """A project, dataset, or item of a migration that has attribute issues."""

    __tablename__ = "migration_entity"
    __table_args__ = (
        # An entity is in a migration once.
        UniqueConstraint(
            "migration_uid", "entity_uid", name="uq_migration_entity_entity"
        ),
    )

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    migration_uid: Mapped[UUID] = mapped_column(
        ForeignKey("project_migration.uid", ondelete="CASCADE"), index=True
    )
    entity_uid: Mapped[UUID] = mapped_column(Uuid)
    """The project, the dataset, or the item."""

    target_entity_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    """The schema of the entity in the target root."""

    identifier: Mapped[str] = mapped_column(Text)
    """The name of the project or dataset, or the identifier of the item, when
    the migration was planned. The project is locked while migrating, so it
    does not change."""

    position: Mapped[int] = mapped_column(Integer)
    """Where the entity is among those of the migration: the project, the
    dataset, then the items by identifier."""

    attribute_issues: Mapped[list[DatabaseAttributeMigrationIssue]] = relationship(
        "DatabaseAttributeMigrationIssue",
        cascade="all, delete-orphan",
        order_by=(
            DatabaseAttributeMigrationIssue.target_attribute_schema_uid.is_(None),
            DatabaseAttributeMigrationIssue.problem,
        ),
    )
    """The attribute issues of the entity, those with a target first, then the
    dropped attributes."""

    def __init__(
        self,
        entity_uid: UUID,
        target_entity_schema_uid: UUID,
        identifier: str,
        position: int,
        attribute_issues: list[DatabaseAttributeMigrationIssue],
    ):
        """Create an entity of a migration with its attribute issues.

        Parameters
        ----------
        entity_uid: UUID
            The project, the dataset, or the item.
        target_entity_schema_uid: UUID
            The target schema of the entity.
        identifier: str
            The name of the project or dataset, or the identifier of the item.
        position: int
            Where the entity is among those of the migration.
        attribute_issues: list[DatabaseAttributeMigrationIssue]
            The attribute issues of the entity.
        """
        super().__init__(
            uid=uuid4(),
            entity_uid=entity_uid,
            target_entity_schema_uid=target_entity_schema_uid,
            identifier=identifier,
            position=position,
            attribute_issues=attribute_issues,
        )

    @property
    def model(self) -> EntityMigrationIssues:
        """Make the model of the entity, with its attribute issues."""
        return EntityMigrationIssues(
            uid=self.entity_uid,
            identifier=self.identifier,
            target_schema_uid=self.target_entity_schema_uid,
            attribute_issues=[issue.model for issue in self.attribute_issues],
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

    previous_project_status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=32)
    )
    """The status the project had, which it gets back."""

    status: Mapped[MigrationStatus] = mapped_column(
        Enum(MigrationStatus, native_enum=False, length=32)
    )
    """Where the migration is."""

    error: Mapped[str | None] = mapped_column(Text)
    """Why planning or completing failed."""

    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    updated: Mapped[datetime.datetime] = mapped_column(DateTime)

    entities: Mapped[list[DatabaseMigrationEntity]] = relationship(
        "DatabaseMigrationEntity",
        cascade="all, delete-orphan",
        order_by=DatabaseMigrationEntity.position,
    )
    """The entities with attribute issues, in their order."""

    def __init__(
        self,
        project_uid: UUID,
        source_root_schema_uid: UUID,
        target_root_schema_uid: UUID,
        previous_project_status: ProjectStatus,
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
        previous_project_status: ProjectStatus
            The status the project has.
        """
        now = datetime.datetime.now()
        super().__init__(
            uid=uuid4(),
            project_uid=project_uid,
            source_root_schema_uid=source_root_schema_uid,
            target_root_schema_uid=target_root_schema_uid,
            previous_project_status=previous_project_status,
            status=MigrationStatus.PLANNING,
            created=now,
            updated=now,
        )

    def set_status(self, status: MigrationStatus, error: str | None = None) -> None:
        """Set the status of the migration, and when it was updated.

        Parameters
        ----------
        status: MigrationStatus
            The status.
        error: str | None = None
            Why planning or completing failed, or None.
        """
        self.status = status
        self.error = error
        self.updated = datetime.datetime.now()

    @property
    def model(self) -> ProjectMigration:
        """Make the model of the migration, with the attribute issues of each
        entity."""
        return ProjectMigration(
            project_uid=self.project_uid,
            source_root_schema_uid=self.source_root_schema_uid,
            target_root_schema_uid=self.target_root_schema_uid,
            previous_project_status=self.previous_project_status,
            status=self.status,
            error=self.error,
            created=self.created,
            updated=self.updated,
            issues=[entity.model for entity in self.entities],
        )
