"""unique attribute per owner and schema, and mapper name without family

An owner holds one attribute of each attribute schema. The unique constraint
over every owner column held nothing, as an attribute row has all owner columns
but one null and nulls are distinct to a unique constraint. It is replaced by a
unique index per owner column over the rows held through it.

A mapper's name is unique within its family, which held nothing for mappers
without a family for the same reason. Their names are made unique among
themselves by an index over them.

Revision ID: 3c8e51f7a2d4
Revises: b96b2d37e486
Create Date: 2026-10-16 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3c8e51f7a2d4"
down_revision: str | None = "b96b2d37e486"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNER_COLUMNS = (
    "attribute_item_uid",
    "private_attribute_item_uid",
    "attribute_project_uid",
    "private_attribute_project_uid",
    "attribute_dataset_uid",
    "private_attribute_dataset_uid",
)

LEGACY_COLUMNS = ("schema_uid", *OWNER_COLUMNS, "mapping_item_uid")
"""The columns of the unique constraint the indexes replace, in its order."""

LEGACY_NAME = "uq_attribute_schema_uid"
"""What the legacy constraint is called where the database has not named it,
as given by the naming convention the batch reflects the table with on SQLite,
and what a downgrade names it."""

MAPPER_INDEX = "uq_mapper_name_without_family"

LISTED = 20
"""How many duplicates the refusal to upgrade names."""


def _attribute_index(owner_column: str) -> str:
    return f"uq_attribute_{owner_column}_schema_uid"


def _attribute_duplicates(bind: sa.engine.Connection) -> list[str]:
    """Describe each owner holding more than one attribute of a schema."""
    duplicates: list[str] = []
    for owner_column in OWNER_COLUMNS:
        attribute = sa.table(
            "attribute", sa.column(owner_column), sa.column("schema_uid")
        )
        owner = attribute.c[owner_column]
        count = sa.func.count()
        rows = bind.execute(
            sa.select(
                owner.label("owner_uid"), attribute.c.schema_uid, count.label("count")
            )
            .where(owner.is_not(None))
            .group_by(owner, attribute.c.schema_uid)
            .having(count > 1)
            .order_by(count.desc())
        ).all()
        duplicates.extend(
            f"  {owner_column} {row.owner_uid} schema {row.schema_uid}: "
            f"{row.count} attributes"
            for row in rows
        )
    return duplicates


def _mapper_duplicates(bind: sa.engine.Connection) -> list[str]:
    """Describe each name held by more than one mapper without a family."""
    rows = bind.execute(
        sa.text(
            "SELECT name, COUNT(*) AS count FROM mapper WHERE family_uid IS NULL "
            "GROUP BY name HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC"
        )
    ).all()
    return [
        f"  mapper name {row.name!r} without family: {row.count} mappers"
        for row in rows
    ]


def _refuse_duplicates(bind: sa.engine.Connection) -> None:
    """Stop rather than repair when the data already breaks the invariants.

    Which of two attributes of an owner to keep, or which of two mappers keeps
    a name, is a decision about the data and not one a migration can take. The
    report names the rows so that the decision can be made.
    """
    duplicates = [*_attribute_duplicates(bind), *_mapper_duplicates(bind)]
    if not duplicates:
        return
    listed = "\n".join(duplicates[:LISTED])
    more = (
        ""
        if len(duplicates) <= LISTED
        else f"\n  ... and {len(duplicates) - LISTED} more"
    )
    raise RuntimeError(
        f"Found {len(duplicates)} duplicated attribute owners or mapper names, "
        f"so the unique indexes cannot be added. Remove or rename the duplicates "
        f"first, as which one survives is a decision about the data:\n"
        f"{listed}{more}"
    )


def _legacy_constraint_name(bind: sa.engine.Connection) -> str | None:
    """The name of the legacy constraint, None where the database has not
    named it."""
    for constraint in sa.inspect(bind).get_unique_constraints("attribute"):
        if set(constraint["column_names"]) == set(LEGACY_COLUMNS):
            return constraint["name"]
    raise RuntimeError("The unique constraint on the attribute owners is missing.")


def upgrade() -> None:
    bind = op.get_bind()
    _refuse_duplicates(bind)
    legacy_name = _legacy_constraint_name(bind)
    with op.batch_alter_table(
        "attribute",
        naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"},
    ) as batch:
        batch.drop_constraint(legacy_name or LEGACY_NAME, type_="unique")
    for owner_column in OWNER_COLUMNS:
        where = sa.text(f"{owner_column} IS NOT NULL")
        op.create_index(
            _attribute_index(owner_column),
            "attribute",
            [owner_column, "schema_uid"],
            unique=True,
            sqlite_where=where,
            postgresql_where=where,
        )
    where = sa.text("family_uid IS NULL")
    op.create_index(
        MAPPER_INDEX,
        "mapper",
        ["name"],
        unique=True,
        sqlite_where=where,
        postgresql_where=where,
    )


def downgrade() -> None:
    op.drop_index(MAPPER_INDEX, table_name="mapper")
    for owner_column in reversed(OWNER_COLUMNS):
        op.drop_index(_attribute_index(owner_column), table_name="attribute")
    # Named, unlike the one the baseline created, as SQLite cannot add an
    # unnamed constraint in a batch. An upgrade finds it by its columns.
    with op.batch_alter_table("attribute") as batch:
        batch.create_unique_constraint(LEGACY_NAME, list(LEGACY_COLUMNS))
