"""add validation review issue source

Revision ID: d2b8f45a6c19
Revises: e4b7a2c93d81
Create Date: 2026-08-19 10:00:00.000000

An item that is not as valid as it is expected to be raises an issue of its
own, rather than only a reason written on the unit above it. Recording it
lets it be settled when the item becomes valid, and lets the unit be cleared
once nothing is left open on it.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2b8f45a6c19"
down_revision: Union[str, None] = "e4b7a2c93d81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SOURCES_BEFORE = (
    "USER",
    "METADATA_IMPORTER",
    "IMAGE_IMPORTER",
)
_SOURCES_AFTER = (*_SOURCES_BEFORE, "VALIDATION")


def _alter_source_enum(sources: tuple[str, ...]) -> None:
    """Alter the review issue source enum to hold the given sources.

    Postgres holds the sources in an enum type, which is altered in place.
    Other dialects hold them in a check constraint on a varchar column, which
    has to be rebuilt to be altered.
    """
    if op.get_bind().dialect.name == "postgresql":
        for source in sources:
            op.execute(
                f"ALTER TYPE reviewissuesource ADD VALUE IF NOT EXISTS '{source}'"
            )
        return
    with op.batch_alter_table("review_issue") as review_issue:
        review_issue.alter_column(
            "source",
            existing_type=sa.Enum(*_SOURCES_BEFORE, name="reviewissuesource"),
            type_=sa.Enum(*sources, name="reviewissuesource"),
            existing_nullable=False,
        )


def upgrade() -> None:
    _alter_source_enum(_SOURCES_AFTER)


def downgrade() -> None:
    # Deleted rather than kept as another source: what validation raised is
    # derived from the items, and is raised again by asking for the invalid
    # ones to be flagged. Calling it something a person or an import raised
    # would leave a record of a decision nobody made.
    op.execute("DELETE FROM review_issue WHERE source = 'VALIDATION'")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE reviewissuesource RENAME TO reviewissuesource_old")
        sa.Enum(*_SOURCES_BEFORE, name="reviewissuesource").create(op.get_bind())
        op.execute(
            "ALTER TABLE review_issue ALTER COLUMN source TYPE reviewissuesource "
            "USING source::text::reviewissuesource"
        )
        op.execute("DROP TYPE reviewissuesource_old")
        return
    _alter_source_enum(_SOURCES_BEFORE)
