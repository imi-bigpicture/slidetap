"""add locked batch status

Revision ID: a3f6d2e91b74
Revises: f2a91c6b37d8
Create Date: 2026-08-13 16:00:00.000000

A batch is locked when it has been curated: everything in it is valid and
closed to editing, and the images wait in the processing folder until the
project is completed.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3f6d2e91b74"
down_revision: Union[str, None] = "b8d3f16c04a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUSES_BEFORE = (
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
)
_STATUSES_AFTER = (*_STATUSES_BEFORE, "LOCKED")


def _alter_status_enum(statuses: tuple[str, ...]) -> None:
    """Alter the batch status enum to hold the given statuses.

    Postgres holds the statuses in an enum type, which is altered in place.
    Other dialects hold them in a check constraint on a varchar column, which
    has to be rebuilt to be altered.
    """
    if op.get_bind().dialect.name == "postgresql":
        for status in statuses:
            op.execute(f"ALTER TYPE batchstatus ADD VALUE IF NOT EXISTS '{status}'")
        return
    with op.batch_alter_table("batch") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.Enum(*_STATUSES_BEFORE, name="batchstatus"),
            type_=sa.Enum(*statuses, name="batchstatus"),
            existing_nullable=False,
        )


def upgrade() -> None:
    _alter_status_enum(_STATUSES_AFTER)


def downgrade() -> None:
    # Postgres cannot drop a value from an enum type. A batch locked after the
    # upgrade goes back to the status it was locked from; what it holds stays
    # locked, which the reopen it can no longer be given would have undone.
    op.execute(
        "UPDATE batch SET status = 'IMAGE_POST_PROCESSING_COMPLETE' "
        "WHERE status = 'LOCKED'"
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE batchstatus RENAME TO batchstatus_old")
        sa.Enum(*_STATUSES_BEFORE, name="batchstatus").create(op.get_bind())
        op.execute(
            "ALTER TABLE batch ALTER COLUMN status TYPE batchstatus "
            "USING status::text::batchstatus"
        )
        op.execute("DROP TYPE batchstatus_old")
        return
    _alter_status_enum(_STATUSES_BEFORE)
