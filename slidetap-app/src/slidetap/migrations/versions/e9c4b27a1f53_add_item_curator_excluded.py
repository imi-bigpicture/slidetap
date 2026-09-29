"""add item curator excluded

Revision ID: e9c4b27a1f53
Revises: d8a4c5f19e6b
Create Date: 2026-09-28 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9c4b27a1f53"
down_revision: Union[str, None] = "d8a4c5f19e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "item",
        sa.Column(
            "curator_excluded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Nothing recorded why an item went, so it is read off what is left: an
    # item out of the project under nothing that is out went on its own, and a
    # curator took it out. One under something that is out is taken to have
    # gone with it, and a later cascade may bring it back.
    item = sa.table(
        "item",
        sa.column("uid", sa.Uuid()),
        sa.column("selected", sa.Boolean()),
        sa.column("curator_excluded", sa.Boolean()),
    )
    holder = item.alias("holder")
    sample_to_sample = sa.table(
        "sample_to_sample",
        sa.column("parent_uid", sa.Uuid()),
        sa.column("child_uid", sa.Uuid()),
    )
    sample_to_image = sa.table(
        "sample_to_image",
        sa.column("sample_uid", sa.Uuid()),
        sa.column("image_uid", sa.Uuid()),
    )
    annotation = sa.table(
        "annotation", sa.column("uid", sa.Uuid()), sa.column("image_uid", sa.Uuid())
    )
    observation = sa.table(
        "observation",
        sa.column("uid", sa.Uuid()),
        sa.column("image_uid", sa.Uuid()),
        sa.column("sample_uid", sa.Uuid()),
        sa.column("annotation_uid", sa.Uuid()),
    )

    under_something_out = sa.or_(
        sa.exists(
            sa.select(sa.literal(1))
            .select_from(
                sample_to_sample.join(
                    holder, holder.c.uid == sample_to_sample.c.parent_uid
                )
            )
            .where(
                sample_to_sample.c.child_uid == item.c.uid,
                holder.c.selected.is_(False),
            )
        ),
        sa.exists(
            sa.select(sa.literal(1))
            .select_from(
                sample_to_image.join(
                    holder, holder.c.uid == sample_to_image.c.sample_uid
                )
            )
            .where(
                sample_to_image.c.image_uid == item.c.uid,
                holder.c.selected.is_(False),
            )
        ),
        sa.exists(
            sa.select(sa.literal(1))
            .select_from(annotation.join(holder, holder.c.uid == annotation.c.image_uid))
            .where(annotation.c.uid == item.c.uid, holder.c.selected.is_(False))
        ),
        sa.exists(
            sa.select(sa.literal(1))
            .select_from(
                observation.join(
                    holder,
                    sa.or_(
                        holder.c.uid == observation.c.image_uid,
                        holder.c.uid == observation.c.sample_uid,
                        holder.c.uid == observation.c.annotation_uid,
                    ),
                )
            )
            .where(observation.c.uid == item.c.uid, holder.c.selected.is_(False))
        ),
    )
    op.execute(
        item.update()
        .where(item.c.selected.is_(False), sa.not_(under_something_out))
        .values(curator_excluded=True)
    )


def downgrade() -> None:
    op.drop_column("item", "curator_excluded")
