"""add attribute rejected values

Revision ID: e4b7a2c93d81
Revises: c8b1e47d2a56
Create Date: 2026-08-19 09:00:00.000000

What an item came in with that a curator has refused: the value it was imported
with, the text mappers read, or both. Nothing is refused for what is already
there, which is what zero means.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4b7a2c93d81"
down_revision: Union[str, None] = "c8b1e47d2a56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attribute",
        sa.Column("rejected", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("attribute", "rejected")
