"""add schema migration

The migration of a project to another root schema, from it is started until
it is completed or aborted, and its issues: what the migration could not
convert, for the curator to decide.

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
        "schema_migration",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("project_uid", sa.Uuid(), nullable=False),
        sa.Column("source_root_schema_uid", sa.Uuid(), nullable=False),
        sa.Column("target_root_schema_uid", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("dropped", sa.JSON(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_uid"], ["project.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("project_uid"),
    )
    op.create_table(
        "schema_migration_issue",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("migration_uid", sa.Uuid(), nullable=False),
        sa.Column("object_uid", sa.Uuid(), nullable=False),
        sa.Column("object_kind", sa.String(length=32), nullable=False),
        sa.Column("object_schema_uid", sa.Uuid(), nullable=False),
        sa.Column("tag", sa.String(length=128), nullable=False),
        sa.Column("original", sa.JSON(), nullable=False),
        sa.Column("proposed", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decision", sa.JSON(), nullable=True),
        sa.Column("decided", sa.Boolean(), nullable=False),
        sa.Column("left_empty", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["migration_uid"], ["schema_migration.uid"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("migration_uid", "object_uid", "tag"),
    )
    op.create_index(
        "ix_schema_migration_issue_migration_uid",
        "schema_migration_issue",
        ["migration_uid"],
    )


def downgrade() -> None:
    # A project being migrated is as it was until the migration is completed,
    # and goes back to the status it had.
    previous = (
        "SELECT schema_migration.previous_status FROM schema_migration "
        "WHERE schema_migration.project_uid = project.uid"
    )
    if op.get_bind().dialect.name == "postgresql":
        previous = f"CAST(({previous}) AS projectstatus)"
    else:
        previous = f"({previous})"
    op.execute(
        f"UPDATE project SET status = {previous} "
        "WHERE uid IN (SELECT project_uid FROM schema_migration)"
    )
    op.drop_index(
        "ix_schema_migration_issue_migration_uid", table_name="schema_migration_issue"
    )
    op.drop_table("schema_migration_issue")
    op.drop_table("schema_migration")
