"""add storage folder

Revision ID: b6f4a80c2d17
Revises: c9e2a71f4b38
Create Date: 2026-08-21 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b6f4a80c2d17"
down_revision: Union[str, None] = "c9e2a71f4b38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Left empty rather than backfilled from the current names: the folder is
    # claimed the first time a project or dataset is stored to, and a project
    # that has stored nothing has no folder to freeze. A project that has stored
    # something claims, on its next store, the same folder its name already gave
    # it, so nothing on disk moves.
    op.add_column(
        "project", sa.Column("storage_folder", sa.String(length=256), nullable=True)
    )
    op.add_column(
        "dataset", sa.Column("storage_folder", sa.String(length=256), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("dataset", "storage_folder")
    op.drop_column("project", "storage_folder")
