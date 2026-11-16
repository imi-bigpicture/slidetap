"""mapping expression text

Widens `mapping_item.expression` and `mapping_item.literal` from a string of
128 characters to text: a regex expression that reads past qualifiers and
guards against a second answer runs to several hundred characters, and was
refused.

Revision ID: 8e80bce7223a
Revises: 8d2f6a1c9e47
Create Date: 2026-11-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8e80bce7223a"
down_revision: str | None = "8d2f6a1c9e47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (("expression", False), ("literal", True))


def upgrade() -> None:
    with op.batch_alter_table("mapping_item") as batch:
        for column, nullable in _COLUMNS:
            batch.alter_column(
                column,
                existing_type=sa.String(128),
                type_=sa.Text(),
                existing_nullable=nullable,
            )


def downgrade() -> None:
    # Fails where an expression is longer than 128 characters, which a string
    # of 128 cannot hold: those mapping items have to be removed first.
    with op.batch_alter_table("mapping_item") as batch:
        for column, nullable in _COLUMNS:
            batch.alter_column(
                column,
                existing_type=sa.Text(),
                type_=sa.String(128),
                existing_nullable=nullable,
            )
