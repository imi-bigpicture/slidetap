"""add mapping item literal column

Revision ID: 70048a43fda6
Revises: e7a1b93d4c26
Create Date: 2026-07-23 10:21:56.347515

"""

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "70048a43fda6"
down_revision: Union[str, None] = "e7a1b93d4c26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_mapping_item_mapper_literal"


def _literal_key(expression: str) -> str | None:
    """Frozen copy of `slidetap.util.mapper_matching.literal_key` at the time
    this migration was written.

    Migrations must not import live application code: a later change to the
    real `literal_key` would silently change what this migration backfills
    when replayed from scratch on a new environment. See the sibling
    unit tests in `tests/util/test_mapper_matching.py` for the behaviour this
    is expected to match.
    """
    body = expression[1:] if expression.startswith("^") else expression
    if not body.endswith("$"):
        return None
    body = body[:-1]
    if body == "" or re.escape(body) != body:
        return None
    return body


def upgrade() -> None:
    with op.batch_alter_table("mapping_item") as batch:
        batch.add_column(sa.Column("literal", sa.String(length=128), nullable=True))

    # Backfill in Python rather than SQL: reusing the same classification
    # logic in the migration itself (frozen above) avoids reimplementing it as
    # a Postgres/SQLite regex, which would risk the two dialects disagreeing.
    mapping_item = sa.table(
        "mapping_item",
        sa.column("uid", sa.Uuid()),
        sa.column("expression", sa.String()),
        sa.column("literal", sa.String()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(mapping_item.c.uid, mapping_item.c.expression)
    ).all()
    updates = [
        {"b_uid": uid, "b_literal": literal}
        for uid, expression in rows
        if (literal := _literal_key(expression)) is not None
    ]
    if updates:
        connection.execute(
            mapping_item.update()
            .where(mapping_item.c.uid == sa.bindparam("b_uid"))
            .values(literal=sa.bindparam("b_literal")),
            updates,
        )

    with op.batch_alter_table("mapping_item") as batch:
        batch.create_index(_INDEX, ["mapper_uid", "literal"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("mapping_item") as batch:
        batch.drop_index(_INDEX)
        batch.drop_column("literal")
