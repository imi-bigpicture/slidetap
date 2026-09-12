"""unique pseudonym per dataset and schema

Revision ID: a1c48f6b2e07
Revises: b6f4a80c2d17
Create Date: 2026-09-11 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c48f6b2e07"
down_revision: Union[str, None] = "b6f4a80c2d17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "uq_item_dataset_schema_pseudonym"

_DUPLICATES = sa.text(
    """
    SELECT dataset_uid, schema_uid, pseudonym, COUNT(*) AS count
    FROM item
    WHERE pseudonym IS NOT NULL
    GROUP BY dataset_uid, schema_uid, pseudonym
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
    """
)


def upgrade() -> None:
    """Make one pseudonym standing for one item an invariant the database keeps.

    Stops rather than repairs when a dataset already breaks it, as
    ``f3d9c72e5b18`` does for the identifier: which of two items keeps the
    pseudonym is a decision about the data.
    """
    duplicates = op.get_bind().execute(_DUPLICATES).all()
    if duplicates:
        listed = "\n".join(
            f"  dataset {row.dataset_uid} schema {row.schema_uid} "
            f"pseudonym {row.pseudonym!r}: {row.count} rows"
            for row in duplicates[:20]
        )
        more = (
            "" if len(duplicates) <= 20 else f"\n  ... and {len(duplicates) - 20} more"
        )
        raise RuntimeError(
            f"{len(duplicates)} pseudonyms are held by more than one item, so "
            f"{_CONSTRAINT} cannot be added. Give all but one of each a "
            f"pseudonym of its own first -- which item keeps it decides what "
            f"already handed over under it refers to:\n"
            f"{listed}{more}"
        )
    with op.batch_alter_table("item") as batch:
        batch.create_unique_constraint(
            _CONSTRAINT, ["dataset_uid", "schema_uid", "pseudonym"]
        )


def downgrade() -> None:
    with op.batch_alter_table("item") as batch:
        batch.drop_constraint(_CONSTRAINT, type_="unique")
