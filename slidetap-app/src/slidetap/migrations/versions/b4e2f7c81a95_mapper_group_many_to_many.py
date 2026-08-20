"""mapper to mapper group many-to-many

Revision ID: b4e2f7c81a95
Revises: 70048a43fda6
Create Date: 2026-08-03 09:14:22.118374

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4e2f7c81a95"
down_revision: Union[str, None] = "70048a43fda6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "mapper_to_mapper_group"
_INDEX = "ix_mapper_mapper_group_uid"


def upgrade() -> None:
    """Move group membership from `mapper.mapper_group_uid` to a join table.

    The column allowed a mapper to belong to one group only, so adding a
    mapper to a group silently took it out of the group it was in.
    """
    op.create_table(
        _TABLE,
        sa.Column("mapper_uid", sa.Uuid(), nullable=False),
        sa.Column("mapper_group_uid", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["mapper_uid"], ["mapper.uid"]),
        sa.ForeignKeyConstraint(["mapper_group_uid"], ["mapper_group.uid"]),
        sa.PrimaryKeyConstraint("mapper_uid", "mapper_group_uid"),
    )

    mapper = sa.table(
        "mapper",
        sa.column("uid", sa.Uuid()),
        sa.column("mapper_group_uid", sa.Uuid()),
    )
    join_table = sa.table(
        _TABLE,
        sa.column("mapper_uid", sa.Uuid()),
        sa.column("mapper_group_uid", sa.Uuid()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(mapper.c.uid, mapper.c.mapper_group_uid).where(
            mapper.c.mapper_group_uid.is_not(None)
        )
    ).all()
    if rows:
        connection.execute(
            sa.insert(join_table),
            [
                {"mapper_uid": mapper_uid, "mapper_group_uid": group_uid}
                for mapper_uid, group_uid in rows
            ],
        )

    with op.batch_alter_table("mapper") as batch:
        batch.drop_index(_INDEX)
        batch.drop_column("mapper_group_uid")


def downgrade() -> None:
    """Restore the single group column.

    A mapper that belongs to several groups keeps the group with the lowest
    uid, as the column can only hold one. Membership in the other groups is
    lost.
    """
    with op.batch_alter_table("mapper") as batch:
        batch.add_column(sa.Column("mapper_group_uid", sa.Uuid(), nullable=True))
        batch.create_index(_INDEX, ["mapper_group_uid"], unique=False)

    join_table = sa.table(
        _TABLE,
        sa.column("mapper_uid", sa.Uuid()),
        sa.column("mapper_group_uid", sa.Uuid()),
    )
    mapper = sa.table(
        "mapper",
        sa.column("uid", sa.Uuid()),
        sa.column("mapper_group_uid", sa.Uuid()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            join_table.c.mapper_uid,
            sa.func.min(join_table.c.mapper_group_uid),
        ).group_by(join_table.c.mapper_uid)
    ).all()
    for mapper_uid, group_uid in rows:
        connection.execute(
            sa.update(mapper)
            .where(mapper.c.uid == mapper_uid)
            .values(mapper_group_uid=group_uid)
        )

    op.drop_table(_TABLE)
