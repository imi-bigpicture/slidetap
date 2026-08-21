"""add unmapped value

Revision ID: c9e2a71f4b38
Revises: a7c31e05f9d2
Create Date: 2026-08-20 10:00:00.000000

Which values are waiting for a mapping was a question only a walk could answer:
an attribute hanging off an item is a row, but the ones nested inside it are
JSON in that row, so finding an unmapped one meant reading every attribute of
every item in the project. This holds the answer instead, written as the
attributes are.

Derived in full from those attributes, so it is created empty and filled by
``slidetap-db unmapped-values --rebuild``, which is also the repair if it is
ever suspected of having drifted.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e2a71f4b38"
down_revision: Union[str, None] = "a7c31e05f9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "unmapped_value",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("root_attribute_uid", sa.Uuid(), nullable=False),
        sa.Column("schema_uid", sa.Uuid(), nullable=False),
        sa.Column("value", sa.String(length=512), nullable=False),
        sa.ForeignKeyConstraint(
            ["root_attribute_uid"], ["attribute.uid"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        op.f("ix_unmapped_value_root_attribute_uid"),
        "unmapped_value",
        ["root_attribute_uid"],
    )
    op.create_index(
        op.f("ix_unmapped_value_schema_uid"), "unmapped_value", ["schema_uid"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_unmapped_value_schema_uid"), table_name="unmapped_value")
    op.drop_index(
        op.f("ix_unmapped_value_root_attribute_uid"), table_name="unmapped_value"
    )
    op.drop_table("unmapped_value")
