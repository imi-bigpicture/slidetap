"""index foreign keys

Index the foreign keys that item listings load relations through and that
deleting a batch deletes by. Postgres does not index foreign keys by itself,
so without these each such query reads the whole table.

Revision ID: b96b2d37e486
Revises: 4d2a7f91c3e8
Create Date: 2026-10-15 22:45:49.653040

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b96b2d37e486"
down_revision: Union[str, None] = "4d2a7f91c3e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEXED_COLUMNS = (
    ("annotation", "image_uid"),
    ("batch", "project_uid"),
    ("image_file", "image_uid"),
    ("item_to_tag", "tag_uid"),
    ("metadata_search_item", "item_uid"),
    ("observation", "annotation_uid"),
    ("observation", "image_uid"),
    ("observation", "sample_uid"),
    ("sample_to_image", "image_uid"),
    ("sample_to_sample", "child_uid"),
)


def upgrade() -> None:
    for table, column in INDEXED_COLUMNS:
        op.create_index(f"ix_{table}_{column}", table, [column], unique=False)


def downgrade() -> None:
    for table, column in reversed(INDEXED_COLUMNS):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
