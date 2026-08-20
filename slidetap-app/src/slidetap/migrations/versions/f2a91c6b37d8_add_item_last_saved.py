"""add item last saved

Revision ID: f2a91c6b37d8
Revises: d5c7e18a2f43
Create Date: 2026-08-07 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a91c6b37d8"
down_revision: Union[str, None] = "d5c7e18a2f43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Left empty for existing items rather than backfilled with the time of the
    # migration: nobody saved them then, and a column that claims they were all
    # saved at once is worse than one that admits it does not know.
    op.add_column("item", sa.Column("last_saved", sa.DateTime(), nullable=True))
    op.create_index("ix_item_last_saved", "item", ["last_saved"])


def downgrade() -> None:
    op.drop_index("ix_item_last_saved", table_name="item")
    op.drop_column("item", "last_saved")
