"""mapper family

A mapper belongs to the family of the root schema its attribute is in, and its
name is unique within the family rather than overall: a migration moves a
mapper to the root it migrates to, and the mapping sheets of
every version find it by name.

The family of the mappers already stored is the plugin's to know, and is given
to them when the application starts.

Revision ID: 5c1d8e3a7b42
Revises: e7c2b9a4d513
Create Date: 2026-10-01 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5c1d8e3a7b42"
down_revision: Union[str, None] = "e7c2b9a4d513"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NAME_INDEX = "ix_mapper_name"
_FAMILY_INDEX = "ix_mapper_family_uid"
_UNIQUE = "uq_mapper_name_family_uid"


def upgrade() -> None:
    with op.batch_alter_table("mapper") as batch:
        batch.add_column(sa.Column("family_uid", sa.Uuid(), nullable=True))
        batch.create_index(_FAMILY_INDEX, ["family_uid"], unique=False)
        batch.drop_index(_NAME_INDEX)
        batch.create_index(_NAME_INDEX, ["name"], unique=False)
        batch.create_unique_constraint(_UNIQUE, ["name", "family_uid"])


def downgrade() -> None:
    # Fails where two families have a mapper of the same name, which only this
    # revision allows: which of them to keep is not something to decide here.
    with op.batch_alter_table("mapper") as batch:
        batch.drop_constraint(_UNIQUE, type_="unique")
        batch.drop_index(_NAME_INDEX)
        batch.create_index(_NAME_INDEX, ["name"], unique=True)
        batch.drop_index(_FAMILY_INDEX)
        batch.drop_column("family_uid")
