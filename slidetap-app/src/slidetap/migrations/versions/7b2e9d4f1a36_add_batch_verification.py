"""add batch verification

Rounds of review units drawn at random from a batch to be checked by hand
before the batch is completed, and what was decided about each unit drawn. A
unit failed when verifying raises a review issue of its own source. Items
record when what they hold, or anything under them, last changed, so that a
decision made before a change can be told apart from one made after.

Revision ID: 7b2e9d4f1a36
Revises: 3c8e51f7a2d4
Create Date: 2026-10-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b2e9d4f1a36"
down_revision: str | None = "3c8e51f7a2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SOURCES_BEFORE = (
    "USER",
    "METADATA_IMPORTER",
    "IMAGE_IMPORTER",
    "VALIDATION",
)
_SOURCES_AFTER = (*_SOURCES_BEFORE, "VERIFICATION")


def _alter_source_enum(sources: tuple[str, ...], existing: tuple[str, ...]) -> None:
    """Alter the review issue source enum to hold the given sources.

    Postgres holds the sources in an enum type, which is added to in place.
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
            existing_type=sa.Enum(*existing, name="reviewissuesource"),
            type_=sa.Enum(*sources, name="reviewissuesource"),
            existing_nullable=False,
        )


def upgrade() -> None:
    _alter_source_enum(_SOURCES_AFTER, _SOURCES_BEFORE)
    # Empty for what is already there: nothing has been decided on yet that
    # a change before now could make stale.
    with op.batch_alter_table("item") as item:
        item.add_column(sa.Column("last_changed", sa.DateTime(), nullable=True))
    op.create_table(
        "verification_round",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("batch_uid", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("requested_size", sa.Integer(), nullable=True),
        sa.Column("requested_fraction", sa.Float(), nullable=True),
        sa.Column("population", sa.JSON(), nullable=True),
        sa.Column("population_size", sa.Integer(), nullable=False),
        sa.Column("origin_entry_uid", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["batch_uid"], ["batch.uid"]),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_verification_round_batch_uid", "verification_round", ["batch_uid"]
    )
    op.create_table(
        "verification_entry",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("round_uid", sa.Uuid(), nullable=False),
        sa.Column("unit_uid", sa.Uuid(), nullable=False),
        sa.Column(
            "verdict",
            sa.Enum("PENDING", "PASSED", "FAILED", name="verificationverdict"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["round_uid"], ["verification_round.uid"]),
        sa.ForeignKeyConstraint(["unit_uid"], ["item.uid"]),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("unit_uid", name="uq_verification_entry_unit"),
    )
    op.create_index(
        "ix_verification_entry_round_uid",
        "verification_entry",
        ["round_uid"],
    )


def downgrade() -> None:
    op.drop_index("ix_verification_entry_round_uid", table_name="verification_entry")
    op.drop_table("verification_entry")
    op.drop_index("ix_verification_round_batch_uid", table_name="verification_round")
    op.drop_table("verification_round")
    with op.batch_alter_table("item") as item:
        item.drop_column("last_changed")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS verificationverdict")
    # Deleted rather than kept as another source: what a verifier raised is
    # about a round that no longer exists.
    op.execute("DELETE FROM review_issue WHERE source = 'VERIFICATION'")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE reviewissuesource RENAME TO reviewissuesource_old")
        sa.Enum(*_SOURCES_BEFORE, name="reviewissuesource").create(op.get_bind())
        op.execute(
            "ALTER TABLE review_issue ALTER COLUMN source TYPE reviewissuesource "
            "USING source::text::reviewissuesource"
        )
        op.execute("DROP TYPE reviewissuesource_old")
        return
    _alter_source_enum(_SOURCES_BEFORE, _SOURCES_AFTER)
