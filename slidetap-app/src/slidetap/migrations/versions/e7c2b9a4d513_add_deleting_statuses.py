"""add deleting statuses

Revision ID: e7c2b9a4d513
Revises: e9c4b27a1f53
Create Date: 2026-09-28 12:00:00.000000

A batch or a project is deleting while a background task removes what it
holds. The status is set before the task is deferred and the row goes when the
task commits, so a delete interrupted part-way is visibly unfinished and can
be run again.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7c2b9a4d513"
down_revision: str | None = "e9c4b27a1f53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BATCH_STATUSES_BEFORE = (
    "INITIALIZED",
    "METADATA_SEARCHING",
    "METADATA_SEARCH_COMPLETE",
    "IMAGE_PRE_PROCESSING",
    "IMAGE_PRE_PROCESSING_COMPLETE",
    "IMAGE_POST_PROCESSING",
    "IMAGE_POST_PROCESSING_COMPLETE",
    "COMPLETED",
    "IMAGE_STORING",
    "FAILED",
    "DELETED",
    "LOCKED",
)
_BATCH_STATUSES_AFTER = (*_BATCH_STATUSES_BEFORE, "DELETING")

_PROJECT_STATUSES_BEFORE = (
    "IN_PROGRESS",
    "COMPLETED",
    "EXPORTING",
    "EXPORT_COMPLETE",
    "FAILED",
    "DELETED",
)
_PROJECT_STATUSES_AFTER = (*_PROJECT_STATUSES_BEFORE, "DELETING")


def _alter_status_enum(
    type_name: str,
    table: str,
    statuses_before: tuple[str, ...],
    statuses: tuple[str, ...],
) -> None:
    """Alter a status enum to hold the given statuses.

    Postgres holds the statuses in an enum type, which is altered in place.
    Other dialects hold them in a check constraint on a varchar column, which
    has to be rebuilt to be altered.
    """
    if op.get_bind().dialect.name == "postgresql":
        for status in statuses:
            op.execute(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{status}'")
        return
    with op.batch_alter_table(table) as batch:
        batch.alter_column(
            "status",
            existing_type=sa.Enum(*statuses_before, name=type_name),
            type_=sa.Enum(*statuses, name=type_name),
            existing_nullable=False,
        )


def _restore_status_enum(
    type_name: str,
    table: str,
    statuses_before: tuple[str, ...],
    statuses_after: tuple[str, ...],
) -> None:
    """Take a status enum back to the statuses it held before.

    Postgres cannot drop a value from an enum type, so the type is recreated
    and the column converted to it.
    """
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER TYPE {type_name} RENAME TO {type_name}_old")
        sa.Enum(*statuses_before, name=type_name).create(op.get_bind())
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN status TYPE {type_name} "
            f"USING status::text::{type_name}"
        )
        op.execute(f"DROP TYPE {type_name}_old")
        return
    _alter_status_enum(type_name, table, statuses_after, statuses_before)


def upgrade() -> None:
    _alter_status_enum(
        "batchstatus", "batch", _BATCH_STATUSES_BEFORE, _BATCH_STATUSES_AFTER
    )
    _alter_status_enum(
        "projectstatus", "project", _PROJECT_STATUSES_BEFORE, _PROJECT_STATUSES_AFTER
    )


def downgrade() -> None:
    # A delete that is under way when the schema goes back is left as deleted,
    # which is what an interrupted delete used to leave behind. Running the
    # delete again, once the schema is upgraded, finishes it.
    op.execute("UPDATE batch SET status = 'DELETED' WHERE status = 'DELETING'")
    op.execute("UPDATE project SET status = 'DELETED' WHERE status = 'DELETING'")
    _restore_status_enum(
        "batchstatus", "batch", _BATCH_STATUSES_BEFORE, _BATCH_STATUSES_AFTER
    )
    _restore_status_enum(
        "projectstatus", "project", _PROJECT_STATUSES_BEFORE, _PROJECT_STATUSES_AFTER
    )
