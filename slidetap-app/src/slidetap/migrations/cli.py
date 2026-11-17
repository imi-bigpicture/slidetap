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

"""Migration commands and the startup check that the database is migrated.

``slidetap-db upgrade`` applies pending migrations, ``slidetap-db stamp``
records a revision without running it (for databases whose schema was created
before migrations were introduced). The configuration is built in code rather
than read from alembic.ini, so both work from any working directory in any
deployment that installs slidetap. alembic.ini is for development commands
such as ``alembic revision --autogenerate``.

:func:`assert_up_to_date` is called when the web app and the task worker start,
so a database that has not been migrated fails the boot with instructions
instead of failing later, per request, with missing-column errors.

The target database is given by ``--db-uri`` or, if that is omitted, by the
``SLIDETAP_DBURI`` environment variable.
"""

import logging
import os
import sys
from typing import Annotated

import typer
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session

app = typer.Typer(
    help="Manage the SlideTap database schema. Uses --db-uri or SLIDETAP_DBURI.",
    no_args_is_help=True,
)


def config() -> Config:
    """Alembic configuration pointing at the migrations shipped with the package."""
    config = Config()
    config.set_main_option("script_location", "slidetap:migrations")
    return config


def head_revision() -> str | None:
    """The latest revision shipped with this version of slidetap."""
    return ScriptDirectory.from_config(config()).get_current_head()


def assert_up_to_date(session: Session) -> None:
    """Raise if the database is not at the revision this code was written for.

    Parameters
    ----------
    session : Session
        Session on the database to check, from
        :meth:`DatabaseService.get_session`.

    Raises
    ----------
    RuntimeError
        If the database is at another revision than the packaged head, or has
        no ``alembic_version`` table at all.

    """
    head = head_revision()
    current = MigrationContext.configure(session.connection()).get_current_revision()
    if current == head:
        return
    at = current or "no revision (no alembic_version table)"
    raise RuntimeError(
        f"Database is at {at}, but this version of slidetap expects {head}. "
        f"Run `slidetap-db upgrade` before starting the app (in compose, the "
        f"dbmigrate service does this). If the database was created before "
        f"migrations were introduced and its schema already matches, run "
        f"`slidetap-db stamp {head}` once instead, to record it as migrated "
        f"without re-creating the tables."
    )


DbUri = Annotated[
    str,
    typer.Option(
        "--db-uri",
        envvar="SLIDETAP_DBURI",
        help="Database URL for the target database.",
    ),
]


def _setup(db_uri: str) -> None:
    """Fail early on a missing DSN and make alembic's progress lines visible.

    ``env.py`` only configures logging when run through alembic.ini, so the
    levels it sets are applied here as well.
    """
    if not db_uri:
        print("No database URL. Pass --db-uri or set SLIDETAP_DBURI.", file=sys.stderr)
        raise SystemExit(1)
    # env.py reads the URL from the environment, so a --db-uri wins by being put there.
    os.environ["SLIDETAP_DBURI"] = db_uri
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)-5.5s [%(name)s] %(message)s"
    )
    logging.getLogger("alembic").setLevel(logging.INFO)


@app.command()
def upgrade(db_uri: DbUri = "") -> None:
    """Apply pending migrations, up to the latest revision."""
    _setup(db_uri)
    command.upgrade(config(), "head")


@app.command()
def stamp(
    revision: Annotated[
        str,
        typer.Argument(
            help=(
                "Revision to record. Use head if the schema already matches the "
                "current models, or the baseline revision if it predates later "
                "migrations, which `slidetap-db upgrade` then applies."
            )
        ),
    ] = "head",
    db_uri: DbUri = "",
) -> None:
    """Record a revision as applied without running it.

    Use on a database whose schema was created before migrations were
    introduced, so the next upgrade does not try to re-create its tables.
    """
    _setup(db_uri)
    command.stamp(config(), revision)
    print(f"Stamped database at {revision}.")


@app.command()
def unmapped_values(
    db_uri: DbUri = "",
    rebuild: Annotated[
        bool,
        typer.Option(help="Write the values again, rather than only reporting."),
    ] = False,
    project_uid: Annotated[
        str, typer.Option(help="Only this project, rather than everything.")
    ] = "",
) -> None:
    """Check what is recorded as waiting for a mapping against the attributes.

    The table is derived from the attributes and maintained as they are
    written, so it can only be wrong if something wrote attributes by a path
    that does not record what they carry. This says whether that has happened,
    and with --rebuild puts it right.
    """
    from uuid import UUID

    from slidetap.config import DatabaseConfig
    from slidetap.services.database_service import DatabaseService
    from slidetap.services.repair_service import RepairService

    _setup(db_uri)
    project = UUID(project_uid) if project_uid else None
    # Connected the way the application connects, so that the URL is read and
    # the dialect chosen in one place rather than three.
    database_service = DatabaseService(
        DatabaseConfig(os.environ["SLIDETAP_DBURI"], False)
    )
    repair_service = RepairService(database_service)
    with database_service.get_session() as session:
        differences = repair_service.verify_unmapped_values(project, session=session)
        for difference in differences:
            print(difference)
        print(f"{len(differences)} difference(s).")
        if rebuild:
            written = repair_service.rebuild_unmapped_values(project, session=session)
            session.commit()
            print(f"Rebuilt: {written} value(s) recorded.")


snapshot_app = typer.Typer(
    help=(
        "Take, list, restore and prune snapshots of the database, kept in "
        "SLIDETAP_SNAPSHOTS or else in the snapshots folder of SLIDETAP_STORAGE."
    ),
    no_args_is_help=True,
)
app.add_typer(snapshot_app, name="snapshot")

Folder = Annotated[
    str,
    typer.Option(
        "--folder",
        envvar="SLIDETAP_SNAPSHOTS",
        help="Folder of the snapshots, else the snapshots folder of SLIDETAP_STORAGE.",
    ),
]


def _snapshots(db_uri: str, folder: str):
    """The snapshots of the database, in the folder given or configured."""
    from pathlib import Path

    from slidetap.migrations.snapshot import DatabaseSnapshots

    _setup(db_uri)
    try:
        return DatabaseSnapshots(
            os.environ["SLIDETAP_DBURI"],
            Path(folder) if folder else DatabaseSnapshots.folder_from_environment(),
        )
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error


@snapshot_app.command("create")
def snapshot_create(
    label: Annotated[
        str, typer.Option(help="Why it is taken, such as deploy or before-remap.")
    ] = "manual",
    db_uri: DbUri = "",
    folder: Folder = "",
) -> None:
    """Take a snapshot of the database."""
    snapshots = _snapshots(db_uri, folder)
    snapshot = snapshots.create(label)
    print(
        f"Snapshot {snapshot.name} taken, {snapshot.size / 1e6:.1f} MB, at revision "
        f"{snapshot.revision}, in {snapshots.folder}."
    )


@snapshot_app.command("list")
def snapshot_list(db_uri: DbUri = "", folder: Folder = "") -> None:
    """List the snapshots, oldest first."""
    snapshots = _snapshots(db_uri, folder)
    listed = snapshots.all()
    if not listed:
        print(f"No snapshots in {snapshots.folder}.")
        return
    for snapshot in listed:
        print(
            f"{snapshot.name}  {snapshot.size / 1e6:9.1f} MB  "
            f"revision {snapshot.revision}  {snapshot.label}"
        )


@snapshot_app.command("restore")
def snapshot_restore(
    name: Annotated[str, typer.Argument(help="The snapshot, as listed.")],
    force: Annotated[
        bool,
        typer.Option(help="End the other sessions on the database rather than refuse."),
    ] = False,
    db_uri: DbUri = "",
    folder: Folder = "",
) -> None:
    """Replace what the database holds with a snapshot.

    A snapshot of what it holds now is taken first, so the restore can be
    undone. Stop the app and the worker before: a restore is refused while
    other sessions are connected, unless --force ends them.
    """
    snapshots = _snapshots(db_uri, folder)
    try:
        before = snapshots.restore(name, force=force)
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
    print(f"Restored {name}. What the database held before is snapshot {before.name}.")


@snapshot_app.command("prune")
def snapshot_prune(
    keep: Annotated[int, typer.Option(help="How many of the newest to keep.")] = 10,
    db_uri: DbUri = "",
    folder: Folder = "",
) -> None:
    """Remove all but the newest snapshots."""
    snapshots = _snapshots(db_uri, folder)
    removed = snapshots.prune(keep)
    print(f"Removed {len(removed)} snapshot(s), kept the newest {keep}.")


if __name__ == "__main__":
    app()
