"""drop item review reason

Revision ID: a7c31e05f9d2
Revises: f3d9c72e5b18
Create Date: 2026-08-19 21:00:00.000000

Why a unit is in the queue is what is open on it, which is the issues raised
under it. The column held a copy of whichever of those was raised first, and
nothing rewrote it when that one was settled, so it went on naming something
already dealt with while saying nothing about the rest.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c31e05f9d2"
down_revision: Union[str, None] = "f3d9c72e5b18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("item", "review_reason")


def downgrade() -> None:
    # Comes back empty: what it held is on the issues, and a reason copied back
    # onto the item would be as stale as the ones this removed.
    op.add_column("item", sa.Column("review_reason", sa.String(512), nullable=True))
