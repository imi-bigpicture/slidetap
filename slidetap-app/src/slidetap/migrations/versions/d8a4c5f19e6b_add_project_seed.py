"""add project seed

Revision ID: d8a4c5f19e6b
Revises: c5e93a17b40d
Create Date: 2026-09-18 12:00:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8a4c5f19e6b"
down_revision: Union[str, None] = "c5e93a17b40d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """A per-project secret an importer can derive whatever it needs to from.

    This column has no other job, is never put in the API's ``Project``
    model, and can be cleared once a project is done, taking the derivation
    with it without touching a single existing item.

    Backfilled for every existing project too, in Python rather than a
    database-generated default: it needs to work on SQLite as well as
    Postgres, and there is no large table here to make a per-row loop costly.
    """
    op.add_column("project", sa.Column("seed", sa.Uuid(), nullable=True))
    bind = op.get_bind()
    project = sa.table("project", sa.column("uid", sa.Uuid()), sa.column("seed", sa.Uuid()))
    for row in bind.execute(sa.text("SELECT uid FROM project")).all():
        bind.execute(
            project.update()
            .where(project.c.uid == row.uid)
            .values(seed=uuid.uuid4())
        )


def downgrade() -> None:
    op.drop_column("project", "seed")
