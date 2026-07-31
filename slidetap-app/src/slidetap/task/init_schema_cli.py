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

The target database is given as a libpq-format DSN by ``--db-uri`` or, if that
is omitted, by the ``SLIDETAP_DBURI`` environment variable. The Procrastinate
``App`` is not loaded here; only the DSN is needed.
"""

import sys
from pathlib import Path
from typing import Annotated

import psycopg
import typer
from procrastinate.schema import SchemaManager, migrations_path
from psycopg import sql

TRACKING_TABLE = "slidetap_procrastinate_version"


def _migration_files() -> list[Path]:
    return sorted(migrations_path.glob("*.sql"))


def _table_exists(conn: psycopg.Connection, name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)::text", (name,))
        row = cur.fetchone()
    return row is not None and row[0] is not None


def _ensure_tracking_table(conn: psycopg.Connection) -> None:
    conn.execute(
        sql.SQL("""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                applied_version TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """).format(table=sql.Identifier(TRACKING_TABLE))
    )


def _read_stamp(conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT applied_version FROM {table} WHERE id = 1").format(
                table=sql.Identifier(TRACKING_TABLE)
            )
        )
        row = cur.fetchone()
    return row[0] if row else None


def _write_stamp(conn: psycopg.Connection, version: str) -> None:
    conn.execute(
        sql.SQL("""
            INSERT INTO {table} (id, applied_version) VALUES (1, %s)
            ON CONFLICT (id) DO UPDATE
                SET applied_version = EXCLUDED.applied_version,
                    updated_at = NOW()
            """).format(table=sql.Identifier(TRACKING_TABLE)),
        (version,),
    )


def _apply_fresh(conn: psycopg.Connection, latest: str) -> None:
    conn.execute(SchemaManager.get_schema())
    _ensure_tracking_table(conn)
    _write_stamp(conn, latest)
    print(f"Procrastinate schema applied; stamped at {latest}")


def _stamp_existing(conn: psycopg.Connection, latest: str) -> None:
    _ensure_tracking_table(conn)
    _write_stamp(conn, latest)
    print(
        f"WARNING: procrastinate tables exist but no tracking row found. "
        f"Stamped at {latest}. If your database was set up against an older "
        f"Procrastinate version, review procrastinate/sql/migrations/ and "
        f"apply any files between your real version and {latest} by hand."
    )


def _apply_pending(conn: psycopg.Connection, stamped: str, files: list[Path]) -> None:
    pending = [f for f in files if f.name > stamped]
    if not pending:
        print(f"Procrastinate schema up to date at {stamped}")
        return
    for migration in pending:
        # A query is a literal string, or bytes. The migrations are read from the
        # files Procrastinate ships, and are thus passed as the bytes they are read
        # as, rather than as a string that is not a literal one.
        conn.execute(migration.read_bytes())
        _write_stamp(conn, migration.name)
        conn.commit()
        print(f"Applied {migration.name}")


def _run(dsn: str) -> None:
    files = _migration_files()
    if not files:
        raise SystemExit("No Procrastinate migration files found.")
    latest = files[-1].name

    with psycopg.Connection.connect(dsn, autocommit=False) as conn:
        if not _table_exists(conn, "procrastinate_jobs"):
            _apply_fresh(conn, latest)
            conn.commit()
            return

        if not _table_exists(conn, TRACKING_TABLE):
            _stamp_existing(conn, latest)
            conn.commit()
            return

        stamped = _read_stamp(conn)
        if stamped is None:
            _stamp_existing(conn, latest)
            conn.commit()
            return

        _apply_pending(conn, stamped, files)


def _main(
    db_uri: Annotated[
        str,
        typer.Option(
            "--db-uri",
            envvar="SLIDETAP_DBURI",
            help="libpq-format DSN for the target database.",
        ),
    ] = "",
) -> None:
    """Apply Procrastinate's schema and any pending migrations."""
    if not db_uri:
        print("No database URL. Pass --db-uri or set SLIDETAP_DBURI.", file=sys.stderr)
        raise SystemExit(1)
    _run(db_uri)


def main() -> None:
    typer.run(_main)


if __name__ == "__main__":
    main()
