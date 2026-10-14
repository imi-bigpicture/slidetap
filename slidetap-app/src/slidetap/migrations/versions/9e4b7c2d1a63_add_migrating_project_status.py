"""add migrating project status

A project being moved to another root schema is migrating, which refuses what
would write to it meanwhile.

Revision ID: 9e4b7c2d1a63
Revises: 5c1d8e3a7b42
Create Date: 2026-09-30 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9e4b7c2d1a63"
down_revision: Union[str, None] = "5c1d8e3a7b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUSES_BEFORE = (
    "IN_PROGRESS",
    "COMPLETED",
    "EXPORTING",
    "EXPORT_COMPLETE",
    "FAILED",
    "DELETED",
    "DELETING",
)
_STATUSES_AFTER = (*_STATUSES_BEFORE, "MIGRATING")


def _alter_status_enum(statuses: tuple[str, ...]) -> None:
    """Alter the project status enum to hold the given statuses.

    Postgres holds the statuses in an enum type, which is altered in place.
    Other dialects hold them in a check constraint on a varchar column, which
    has to be rebuilt to be altered.
    """
    if op.get_bind().dialect.name == "postgresql":
        for status in statuses:
            op.execute(f"ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS '{status}'")
        return
    with op.batch_alter_table("project") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.Enum(*_STATUSES_BEFORE, name="projectstatus"),
            type_=sa.Enum(*statuses, name="projectstatus"),
            existing_nullable=False,
        )


def upgrade() -> None:
    _alter_status_enum(_STATUSES_AFTER)


def downgrade() -> None:
    # Postgres cannot drop a value from an enum type. A project left migrating
    # by a migration that never finished is on the root it was on, and goes
    # back to being in progress.
    op.execute("UPDATE project SET status = 'IN_PROGRESS' WHERE status = 'MIGRATING'")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE projectstatus RENAME TO projectstatus_old")
        sa.Enum(*_STATUSES_BEFORE, name="projectstatus").create(op.get_bind())
        op.execute(
            "ALTER TABLE project ALTER COLUMN status TYPE projectstatus "
            "USING status::text::projectstatus"
        )
        op.execute("DROP TYPE projectstatus_old")
        return
    _alter_status_enum(_STATUSES_BEFORE)
