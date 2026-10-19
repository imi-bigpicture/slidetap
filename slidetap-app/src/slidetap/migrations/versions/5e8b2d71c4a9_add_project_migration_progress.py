"""add project migration progress

The step that planning or completing the migration of a project is on, and how
many of its entities are done of how many, for a progress bar.

Revision ID: 5e8b2d71c4a9
Revises: 7b2e9d4f1a36
Create Date: 2026-10-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e8b2d71c4a9"
down_revision: str | None = "7b2e9d4f1a36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The step is held as a string, as the status is.
    op.add_column(
        "project_migration",
        sa.Column("progress_step", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "project_migration", sa.Column("progress_done", sa.Integer(), nullable=True)
    )
    op.add_column(
        "project_migration", sa.Column("progress_total", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("project_migration", "progress_total")
    op.drop_column("project_migration", "progress_done")
    op.drop_column("project_migration", "progress_step")
