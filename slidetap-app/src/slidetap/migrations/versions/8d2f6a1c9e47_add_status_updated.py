"""add status updated

Adds `status_updated` to project, batch and image, kept by
`slidetap.database.status_tracking`. Left empty for existing rows: when their
status last changed is not known, and a guessed time would mislead.

Revision ID: 8d2f6a1c9e47
Revises: 4c7e1b9d2a58
Create Date: 2026-11-10 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8d2f6a1c9e47"
down_revision: str | None = "4c7e1b9d2a58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("project", "batch", "image")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("status_updated", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "status_updated")
