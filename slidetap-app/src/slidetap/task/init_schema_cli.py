#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Apply Procrastinate's bundled schema and incremental migrations.

Procrastinate ships ``schema.sql`` for empty databases and incremental
migration files under ``procrastinate/sql/migrations/`` (named
``MAJOR.MINOR.PATCH_NN_description.sql``), but provides no runner — its
official guidance for non-Django stacks is to apply the files by hand. This
script automates that for SlideTap by tracking the most recently applied
migration filename in a slidetap-owned table.

Why a slidetap-owned runner rather than baking the files into Alembic: the
runner can be deleted in one commit if Procrastinate is ever replaced with
another task framework. Alembic-managed wrappers would leave dead
revisions in slidetap's migration history forever.

Boot behaviour:
  * No ``procrastinate_jobs`` table -> apply ``schema.sql`` and stamp the
    latest bundled migration filename.
  * Table present, no tracking row -> assume the database was set up by a
    prior deploy at the same Procrastinate version, stamp the latest
    bundled filename, and log a warning so operators can investigate if
    they are actually behind.
  * Tracking row present -> apply every migration file whose name sorts
    lexicographically above the stamp, in order, updating the stamp after
    each successful apply.

Environment:
    ``SLIDETAP_DBURI`` -- libpq-format DSN for the target database. The
        Procrastinate ``App`` is not loaded here; only the DSN is needed.
"""

import asyncio
import os
import sys
from pathlib import Path

import psycopg
from procrastinate.schema import SchemaManager, migrations_path
from psycopg import sql

TRACKING_TABLE = "slidetap_procrastinate_version"


def _migration_files() -> list[Path]:
    return sorted(migrations_path.glob("*.sql"))


async def _table_exists(conn: psycopg.AsyncConnection, name: str) -> bool:
    async with conn.cursor() as cur:
        await cur.execute("SELECT to_regclass(%s)::text", (name,))
        row = await cur.fetchone()
    return row is not None and row[0] is not None


async def _ensure_tracking_table(conn: psycopg.AsyncConnection) -> None:
    await conn.execute(
        sql.SQL("""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                applied_version TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """).format(table=sql.Identifier(TRACKING_TABLE))
    )


async def _read_stamp(conn: psycopg.AsyncConnection) -> str | None:
    async with conn.cursor() as cur:
        await cur.execute(
            sql.SQL("SELECT applied_version FROM {table} WHERE id = 1").format(
                table=sql.Identifier(TRACKING_TABLE)
            )
        )
        row = await cur.fetchone()
    return row[0] if row else None


async def _write_stamp(conn: psycopg.AsyncConnection, version: str) -> None:
    await conn.execute(
        sql.SQL("""
            INSERT INTO {table} (id, applied_version) VALUES (1, %s)
            ON CONFLICT (id) DO UPDATE
                SET applied_version = EXCLUDED.applied_version,
                    updated_at = NOW()
            """).format(table=sql.Identifier(TRACKING_TABLE)),
        (version,),
    )


async def _apply_fresh(conn: psycopg.AsyncConnection, latest: str) -> None:
    await conn.execute(SchemaManager.get_schema())
    await _ensure_tracking_table(conn)
    await _write_stamp(conn, latest)
    print(f"Procrastinate schema applied; stamped at {latest}")


async def _stamp_existing(conn: psycopg.AsyncConnection, latest: str) -> None:
    await _ensure_tracking_table(conn)
    await _write_stamp(conn, latest)
    print(
        f"WARNING: procrastinate tables exist but no tracking row found. "
        f"Stamped at {latest}. If your database was set up against an older "
        f"Procrastinate version, review procrastinate/sql/migrations/ and "
        f"apply any files between your real version and {latest} by hand."
    )


async def _apply_pending(
    conn: psycopg.AsyncConnection, stamped: str, files: list[Path]
) -> None:
    pending = [f for f in files if f.name > stamped]
    if not pending:
        print(f"Procrastinate schema up to date at {stamped}")
        return
    for migration in pending:
        sql = migration.read_text(encoding="utf-8")
        await conn.execute(sql)
        await _write_stamp(conn, migration.name)
        await conn.commit()
        print(f"Applied {migration.name}")


async def _run(dsn: str) -> None:
    files = _migration_files()
    if not files:
        raise SystemExit("No Procrastinate migration files found.")
    latest = files[-1].name

    async with await psycopg.AsyncConnection.connect(dsn, autocommit=False) as conn:
        if not await _table_exists(conn, "procrastinate_jobs"):
            await _apply_fresh(conn, latest)
            await conn.commit()
            return

        if not await _table_exists(conn, TRACKING_TABLE):
            await _stamp_existing(conn, latest)
            await conn.commit()
            return

        stamped = await _read_stamp(conn)
        if stamped is None:
            await _stamp_existing(conn, latest)
            await conn.commit()
            return

        await _apply_pending(conn, stamped, files)


def main() -> None:
    dsn = os.environ.get("SLIDETAP_DBURI")
    if not dsn:
        print("SLIDETAP_DBURI is not set.", file=sys.stderr)
        raise SystemExit(1)
    asyncio.run(_run(dsn))


if __name__ == "__main__":
    main()
