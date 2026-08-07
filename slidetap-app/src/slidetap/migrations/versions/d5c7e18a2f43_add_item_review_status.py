"""add item review status

Revision ID: d5c7e18a2f43
Revises: b4e2f7c81a95
Create Date: 2026-08-07 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5c7e18a2f43"
down_revision: Union[str, None] = "b4e2f7c81a95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REVIEW_STATUS = sa.Enum(
    "NOT_REVIEWED",
    "FLAGGED",
    "REVIEWED",
    name="reviewstatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    REVIEW_STATUS.create(bind, checkfirst=True)
    # Existing items have never been reviewed and nothing has asked for them,
    # which is what NOT_REVIEWED means, so no backfill beyond the default.
    op.add_column(
        "item",
        sa.Column(
            "review_status",
            REVIEW_STATUS,
            nullable=False,
            server_default="NOT_REVIEWED",
        ),
    )
    op.add_column("item", sa.Column("review_reason", sa.String(512), nullable=True))
    op.create_index("ix_item_review_status", "item", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_item_review_status", table_name="item")
    op.drop_column("item", "review_reason")
    op.drop_column("item", "review_status")
    REVIEW_STATUS.drop(op.get_bind(), checkfirst=True)
