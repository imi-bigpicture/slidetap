"""project exported

When an export of a project last completed. A project that was exported keeps
the schema it was exported with, and the status cannot tell, as an exported
project can be taken back into progress.

The projects already exported are taken to be those whose export is complete,
with the time of the upgrade, as when they were exported is not recorded. One
exported and taken back into progress since is not found.

Revision ID: 2f8a6d4c9b17
Revises: 9e4b7c2d1a63
Create Date: 2026-10-01 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2f8a6d4c9b17"
down_revision: Union[str, None] = "9e4b7c2d1a63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("project") as batch:
        batch.add_column(sa.Column("exported", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE project SET exported = CURRENT_TIMESTAMP "
        "WHERE status = 'EXPORT_COMPLETE'"
    )


def downgrade() -> None:
    with op.batch_alter_table("project") as batch:
        batch.drop_column("exported")
