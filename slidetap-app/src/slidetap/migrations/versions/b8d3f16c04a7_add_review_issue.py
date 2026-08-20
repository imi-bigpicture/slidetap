"""add review issue

Revision ID: b8d3f16c04a7
Revises: f2a91c6b37d8
Create Date: 2026-08-15 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8d3f16c04a7"
down_revision: Union[str, None] = "f2a91c6b37d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A table rather than another column on the item: an item can have more
    # than one issue open at once, each raised on its own and settled on its
    # own, which a single reason column cannot hold.
    op.create_table(
        "review_issue",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("item_uid", sa.Uuid(), nullable=False),
        sa.Column("review_unit_uid", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "USER",
                "METADATA_IMPORTER",
                "IMAGE_IMPORTER",
                name="reviewissuesource",
            ),
            nullable=False,
        ),
        sa.Column("raised_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["item_uid"], ["item.uid"]),
        sa.ForeignKeyConstraint(["review_unit_uid"], ["item.uid"]),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_review_issue_item_uid", "review_issue", ["item_uid"])
    op.create_index(
        "ix_review_issue_review_unit_uid", "review_issue", ["review_unit_uid"]
    )


def downgrade() -> None:
    op.drop_index("ix_review_issue_review_unit_uid", table_name="review_issue")
    op.drop_index("ix_review_issue_item_uid", table_name="review_issue")
    op.drop_table("review_issue")
