"""keep what a search item was imported from

Revision ID: c5e93a17b40d
Revises: a1c48f6b2e07
Create Date: 2026-09-11 12:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5e93a17b40d"
down_revision: Union[str, None] = "a1c48f6b2e07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Give the search item room for what the importer imported it from."""
    with op.batch_alter_table("metadata_search_item") as batch:
        batch.add_column(sa.Column("search_parameters", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("metadata_search_item") as batch:
        batch.drop_column("search_parameters")
