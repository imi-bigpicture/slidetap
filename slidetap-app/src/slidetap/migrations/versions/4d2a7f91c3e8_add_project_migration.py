"""add project migration

The migration of a project to another root schema, from it is created until
it is completed or reverted, and its attribute issues: what the migration
could not convert, for the curator to resolve, and the attributes it dropped,
for the curator to accept.

Revision ID: 4d2a7f91c3e8
Revises: 2f8a6d4c9b17
Create Date: 2026-10-07 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4d2a7f91c3e8"
down_revision: Union[str, None] = "2f8a6d4c9b17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The enums are held as strings: the previous status is a project status,
    # whose Postgres type is the project table's.
    op.create_table(
        "project_migration",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("project_uid", sa.Uuid(), nullable=False),
        sa.Column("source_root_schema_uid", sa.Uuid(), nullable=False),
        sa.Column("target_root_schema_uid", sa.Uuid(), nullable=False),
        sa.Column("previous_project_status", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_uid"], ["project.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("project_uid"),
    )
    op.create_table(
        "migration_attribute_issue",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("migration_uid", sa.Uuid(), nullable=False),
        sa.Column("object_uid", sa.Uuid(), nullable=False),
        sa.Column("target_object_schema_uid", sa.Uuid(), nullable=False),
        sa.Column("source_attribute_schema_uid", sa.Uuid(), nullable=True),
        sa.Column("target_attribute_schema_uid", sa.Uuid(), nullable=True),
        sa.Column("original", sa.JSON(), nullable=True),
        sa.Column("proposed", sa.JSON(), nullable=True),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("resolved", sa.JSON(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["migration_uid"], ["project_migration.uid"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("uid"),
        sa.CheckConstraint(
            "source_attribute_schema_uid IS NOT NULL "
            "OR target_attribute_schema_uid IS NOT NULL",
            name="ck_migration_attribute_issue_attribute_schema",
        ),
    )
    op.create_index(
        "ix_migration_attribute_issue_migration_uid",
        "migration_attribute_issue",
        ["migration_uid"],
    )
    # An issue with a target is unique by it, a dropped attribute by its source.
    op.create_index(
        "uq_migration_attribute_issue_target",
        "migration_attribute_issue",
        ["migration_uid", "object_uid", "target_attribute_schema_uid"],
        unique=True,
        sqlite_where=sa.text("target_attribute_schema_uid IS NOT NULL"),
        postgresql_where=sa.text("target_attribute_schema_uid IS NOT NULL"),
    )
    op.create_index(
        "uq_migration_attribute_issue_dropped",
        "migration_attribute_issue",
        ["migration_uid", "object_uid", "source_attribute_schema_uid"],
        unique=True,
        sqlite_where=sa.text("target_attribute_schema_uid IS NULL"),
        postgresql_where=sa.text("target_attribute_schema_uid IS NULL"),
    )


def downgrade() -> None:
    # A project being migrated is as it was until the migration is completed,
    # and goes back to the status it had.
    previous = (
        "SELECT project_migration.previous_project_status FROM project_migration "
        "WHERE project_migration.project_uid = project.uid"
    )
    if op.get_bind().dialect.name == "postgresql":
        previous = f"CAST(({previous}) AS projectstatus)"
    else:
        previous = f"({previous})"
    op.execute(
        f"UPDATE project SET status = {previous} "
        "WHERE uid IN (SELECT project_uid FROM project_migration)"
    )
    op.drop_index(
        "uq_migration_attribute_issue_dropped",
        table_name="migration_attribute_issue",
    )
    op.drop_index(
        "uq_migration_attribute_issue_target",
        table_name="migration_attribute_issue",
    )
    op.drop_index(
        "ix_migration_attribute_issue_migration_uid",
        table_name="migration_attribute_issue",
    )
    op.drop_table("migration_attribute_issue")
    op.drop_table("project_migration")
