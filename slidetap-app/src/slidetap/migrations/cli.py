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

Environment:
    ``SLIDETAP_DBURI`` -- database URL for the target database, read by
        ``migrations/env.py``.
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
    help="Manage the SlideTap database schema. Reads SLIDETAP_DBURI.",
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


def _setup() -> None:
    """Fail early on a missing DSN and make alembic's progress lines visible.

    ``env.py`` only configures logging when run through alembic.ini, so the
    levels it sets are applied here as well.
    """
    if not os.environ.get("SLIDETAP_DBURI"):
        print("SLIDETAP_DBURI is not set.", file=sys.stderr)
        raise SystemExit(1)
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)-5.5s [%(name)s] %(message)s"
    )
    logging.getLogger("alembic").setLevel(logging.INFO)


@app.command()
def upgrade() -> None:
    """Apply pending migrations, up to the latest revision."""
    _setup()
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
) -> None:
    """Record a revision as applied without running it.

    Use on a database whose schema was created before migrations were
    introduced, so the next upgrade does not try to re-create its tables.
    """
    _setup()
    command.stamp(config(), revision)
    print(f"Stamped database at {revision}.")


if __name__ == "__main__":
    app()
