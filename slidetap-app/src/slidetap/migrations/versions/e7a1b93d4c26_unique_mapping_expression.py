"""unique mapping expression per mapper

Revision ID: e7a1b93d4c26
Revises: c1d4f8a2b6e5
Create Date: 2026-07-14 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "e7a1b93d4c26"
down_revision: Union[str, None] = "c1d4f8a2b6e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "uq_mapping_item_mapper_uid_expression"


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM mapping_item
        WHERE uid NOT IN (
            SELECT uid FROM (
                SELECT uid,
                       ROW_NUMBER() OVER (
                           PARTITION BY mapper_uid, expression
                           ORDER BY hits DESC, uid
                       ) AS row_number
                FROM mapping_item
            ) ranked
            WHERE row_number = 1
        )
        """
    )
    with op.batch_alter_table("mapping_item") as batch:
        batch.create_unique_constraint(_CONSTRAINT, ["mapper_uid", "expression"])


def downgrade() -> None:
    with op.batch_alter_table("mapping_item") as batch:
        batch.drop_constraint(_CONSTRAINT, type_="unique")
