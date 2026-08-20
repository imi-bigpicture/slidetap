"""add batch status message

Revision ID: c1d4f8a2b6e5
Revises: 9a1f2c4e7d10
Create Date: 2026-07-14 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1d4f8a2b6e5"
down_revision: Union[str, None] = "9a1f2c4e7d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("batch", sa.Column("status_message", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("batch", "status_message")
