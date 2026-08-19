"""unique item per dataset, schema and identifier

Revision ID: f3d9c72e5b18
Revises: d2b8f45a6c19
Create Date: 2026-08-19 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3d9c72e5b18"
down_revision: Union[str, None] = "d2b8f45a6c19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "uq_item_dataset_schema_identifier"

_DUPLICATES = sa.text(
    """
    SELECT dataset_uid, schema_uid, identifier, COUNT(*) AS count
    FROM item
    GROUP BY dataset_uid, schema_uid, identifier
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
    """
)


def upgrade() -> None:
    """Make the dedup the importer performs an invariant the database keeps.

    Stops rather than repairs when the data already breaks it. A duplicate item
    holds children, attributes and review issues of its own, so which of the
    two to keep and what to do with what hangs off the other is a decision
    about the data, not one a migration can take. The report names the rows so
    that decision can be made.
    """
    duplicates = op.get_bind().execute(_DUPLICATES).all()
    if duplicates:
        listed = "\n".join(
            f"  dataset {row.dataset_uid} schema {row.schema_uid} "
            f"identifier {row.identifier!r}: {row.count} rows"
            for row in duplicates[:20]
        )
        more = "" if len(duplicates) <= 20 else f"\n  ... and {len(duplicates) - 20} more"
        raise RuntimeError(
            f"{len(duplicates)} identifiers hold more than one item, so "
            f"{_CONSTRAINT} cannot be added. Merge or remove the duplicates "
            f"first -- each carries its own children, attributes and review "
            f"issues, so which row survives is a decision about the data:\n"
            f"{listed}{more}"
        )
    with op.batch_alter_table("item") as batch:
        batch.create_unique_constraint(
            _CONSTRAINT, ["dataset_uid", "schema_uid", "identifier"]
        )


def downgrade() -> None:
    with op.batch_alter_table("item") as batch:
        batch.drop_constraint(_CONSTRAINT, type_="unique")
