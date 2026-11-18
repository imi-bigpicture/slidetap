"""add image file checksum

Adds `checksum` to image_file: the SHA-256 of a file as stored to the outbox.
Left empty for files stored before; an export reads those to checksum them.

Revision ID: c3a9e5f1d7b2
Revises: 8e80bce7223a
Create Date: 2026-11-18 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3a9e5f1d7b2"
down_revision: str | None = "8e80bce7223a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "image_file", sa.Column("checksum", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("image_file", "checksum")
