"""add stored image status

Revision ID: 9a1f2c4e7d10
Revises: 6b3c3c59c3e3
Create Date: 2026-07-13 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9a1f2c4e7d10"
down_revision: Union[str, None] = "6b3c3c59c3e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUSES_BEFORE = (
    "NOT_STARTED",
    "DOWNLOADING",
    "DOWNLOADING_FAILED",
    "DOWNLOADED",
    "PRE_PROCESSING",
    "PRE_PROCESSING_FAILED",
    "PRE_PROCESSED",
    "POST_PROCESSING",
    "POST_PROCESSING_FAILED",
    "POST_PROCESSED",
)
_STATUSES_AFTER = (*_STATUSES_BEFORE, "STORING", "STORING_FAILED", "STORED")


def _alter_status_enum(statuses: tuple[str, ...]) -> None:
    """Alter the image status enum to hold the given statuses.

    Postgres holds the statuses in an enum type, which is altered in place.
    Other dialects hold them in a check constraint on a varchar column, which
    has to be rebuilt to be altered.
    """
    if op.get_bind().dialect.name == "postgresql":
        for status in statuses:
            op.execute(f"ALTER TYPE imagestatus ADD VALUE IF NOT EXISTS '{status}'")
        return
    with op.batch_alter_table("image") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.Enum(*_STATUSES_BEFORE, name="imagestatus"),
            type_=sa.Enum(*statuses, name="imagestatus"),
            existing_nullable=False,
        )


def upgrade() -> None:
    _alter_status_enum(_STATUSES_AFTER)


def downgrade() -> None:
    # Postgres cannot drop a value from an enum type. Images stored after the
    # upgrade have to be set back to a status the enum held before it.
    op.execute(
        "UPDATE image SET status = 'POST_PROCESSED' "
        "WHERE status IN ('STORING', 'STORING_FAILED', 'STORED')"
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE imagestatus RENAME TO imagestatus_old")
        sa.Enum(*_STATUSES_BEFORE, name="imagestatus").create(op.get_bind())
        op.execute(
            "ALTER TABLE image ALTER COLUMN status TYPE imagestatus "
            "USING status::text::imagestatus"
        )
        op.execute("DROP TYPE imagestatus_old")
        return
    _alter_status_enum(_STATUSES_BEFORE)
