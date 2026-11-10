"""add batch export

Adds `batch.storage_folder`, set when a batch is first stored into a bundle of
its own, and the EXPORTING and EXPORTED batch statuses.

Revision ID: 4c7e1b9d2a58
Revises: 5e8b2d71c4a9
Create Date: 2026-10-28 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4c7e1b9d2a58"
down_revision: str | None = "5e8b2d71c4a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
    "LOCKED",
    "DELETING",
)
_STATUSES_AFTER = (*_STATUSES_BEFORE, "EXPORTING", "EXPORTED")


def _alter_status_enum(
    statuses_before: tuple[str, ...], statuses: tuple[str, ...]
) -> None:
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
            existing_type=sa.Enum(*statuses_before, name="batchstatus"),
            type_=sa.Enum(*statuses, name="batchstatus"),
            existing_nullable=False,
        )


def upgrade() -> None:
    _alter_status_enum(_STATUSES_BEFORE, _STATUSES_AFTER)
    # Empty: no existing batch is stored on its own.
    op.add_column(
        "batch", sa.Column("storage_folder", sa.String(length=256), nullable=True)
    )


def downgrade() -> None:
    # Exporting and exported batches revert to completed, as their images are
    # in the outbox.
    op.execute(
        "UPDATE batch SET status = 'COMPLETED' "
        "WHERE status IN ('EXPORTING', 'EXPORTED')"
    )
    op.drop_column("batch", "storage_folder")
    if op.get_bind().dialect.name == "postgresql":
        # Postgres cannot drop a value from an enum type, so the type is
        # recreated and the column converted to it.
        op.execute("ALTER TYPE batchstatus RENAME TO batchstatus_old")
        sa.Enum(*_STATUSES_BEFORE, name="batchstatus").create(op.get_bind())
        op.execute(
            "ALTER TABLE batch ALTER COLUMN status TYPE batchstatus "
            "USING status::text::batchstatus"
        )
        op.execute("DROP TYPE batchstatus_old")
        return
    _alter_status_enum(_STATUSES_AFTER, _STATUSES_BEFORE)
