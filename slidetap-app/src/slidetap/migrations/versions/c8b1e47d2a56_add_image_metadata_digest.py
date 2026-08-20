"""add image metadata digest and source metadata

Revision ID: c8b1e47d2a56
Revises: a3f6d2e91b74
Create Date: 2026-08-13 18:00:00.000000

A fingerprint of the metadata written into an image's files, so that storing
the image can tell whether it has to be written again, and what the image file
itself said before it was converted, so that writing the metadata again fills
in from the file rather than from what the application last wrote. Null for
images converted before this, which are stored as they are.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8b1e47d2a56"
down_revision: Union[str, None] = "a3f6d2e91b74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("image", sa.Column("metadata_digest", sa.String(64), nullable=True))
    op.add_column("image", sa.Column("source_metadata", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("image", "source_metadata")
    op.drop_column("image", "metadata_digest")
