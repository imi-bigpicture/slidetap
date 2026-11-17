#    Copyright 2026 SECTRA AB
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

"""Snapshots of the database, to take before something changes it and to go
back to if the change was wrong.

A snapshot is a file in a folder, with a small JSON file beside it saying what
it is: when it was taken, why, and which revision the database was at. A
Postgres database is snapshot with ``pg_dump`` in its compressed format and
restored with ``pg_restore``, which the image needs the Postgres client tools
for; a SQLite database is copied with SQLite's own backup.

Restoring replaces what the database holds. It is refused while anything else
is connected to a Postgres database, as the app and the worker would go on
writing what the restore removes, and takes a snapshot of what is there first,
so that a restore can itself be undone.
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
from collections.abc import Sequence
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url


@dataclass(frozen=True)
class Snapshot:
    """A snapshot of the database, as its JSON file describes it."""

    name: str
    """The name the snapshot is told apart by, its file name without the
    extension."""
    label: str
    """Why it was taken, such as ``deploy`` or ``before-remap``."""
    created: str
    """When it was taken, in UTC, as an ISO 8601 time."""
    revision: str | None
    """The migration revision the database was at, None where it had none."""
    dialect: str
    """``postgresql`` or ``sqlite``."""
    file: str
    """The file name of the snapshot in the folder."""
    size: int
    """The size of the snapshot file, in bytes."""


class DatabaseSnapshots:
    """Takes, lists, restores and prunes the snapshots of a database in a
    folder."""

    FOLDER_VARIABLE = "SLIDETAP_SNAPSHOTS"
    """The environment variable naming the folder, which is otherwise
    ``snapshots`` in the folder ``SLIDETAP_STORAGE`` names."""

    STORAGE_VARIABLE = "SLIDETAP_STORAGE"

    def __init__(self, db_uri: str, folder: Path):
        """
        Parameters
        ----------
        db_uri: str
            The URL of the database, as the app connects to it.
        folder: Path
            The folder the snapshots are kept in, made where missing.
        """
        self._url = make_url(self.sqlalchemy_uri(db_uri))
        self._folder = folder
        if self.dialect not in ("postgresql", "sqlite"):
            raise ValueError(
                f"Snapshots are taken of Postgres and SQLite databases, not "
                f"{self._url.get_backend_name()}."
            )

    @classmethod
    def folder_from_environment(cls) -> Path:
        """The folder ``SLIDETAP_SNAPSHOTS`` names, or else ``snapshots`` in
        the storage folder.

        Raises
        ------
        ValueError
            If neither variable is set.
        """
        folder = os.environ.get(cls.FOLDER_VARIABLE)
        if folder:
            return Path(folder)
        storage = os.environ.get(cls.STORAGE_VARIABLE)
        if storage:
            return Path(storage) / "snapshots"
        raise ValueError(
            f"No folder for the snapshots. Set {cls.FOLDER_VARIABLE}, or "
            f"{cls.STORAGE_VARIABLE} to keep them in its snapshots folder."
        )

    @property
    def dialect(self) -> str:
        return self._url.get_backend_name()

    @property
    def folder(self) -> Path:
        return self._folder

    def create(self, label: str = "manual") -> Snapshot:
        """Take a snapshot of the database.

        Parameters
        ----------
        label: str = "manual"
            Why it is taken, which its name ends with.

        Returns
        -------
        Snapshot
            The snapshot taken.
        """
        self._folder.mkdir(parents=True, exist_ok=True)
        created = datetime.now(UTC)
        extension = ".dump" if self.dialect == "postgresql" else ".sqlite"
        # Named to the second, and numbered where two are taken in one, as a
        # restore takes one just before it restores.
        base = f"{created:%Y%m%d-%H%M%S}-{self.slug(label)}"
        name, number = base, 1
        while (self._folder / f"{name}{extension}").exists() or (
            self._metadata_path(name).exists()
        ):
            number += 1
            name = f"{base}-{number}"
        path = self._folder / f"{name}{extension}"
        revision = self._revision()
        if self.dialect == "postgresql":
            self._run(
                [
                    "pg_dump",
                    "--format=custom",
                    "--no-owner",
                    f"--file={path}",
                    f"--dbname={self._libpq_uri()}",
                ]
            )
        else:
            self._copy_sqlite(self._sqlite_path(), path)
        snapshot = Snapshot(
            name=name,
            label=label,
            created=created.isoformat(timespec="microseconds"),
            revision=revision,
            dialect=self.dialect,
            file=path.name,
            size=path.stat().st_size,
        )
        self._metadata_path(name).write_text(
            json.dumps(asdict(snapshot), indent=2), encoding="utf-8"
        )
        return snapshot

    def all(self) -> list[Snapshot]:
        """The snapshots in the folder, oldest first."""
        if not self._folder.is_dir():
            return []
        snapshots = [
            Snapshot(**json.loads(path.read_text(encoding="utf-8")))
            for path in self._folder.glob("*.json")
        ]
        return sorted(snapshots, key=lambda snapshot: (snapshot.created, snapshot.name))

    def get(self, name: str) -> Snapshot:
        """The snapshot of a name.

        Raises
        ------
        ValueError
            If the folder holds no snapshot of the name.
        """
        for snapshot in self.all():
            if snapshot.name == name:
                return snapshot
        raise ValueError(f"No snapshot {name} in {self._folder}.")

    def restore(self, name: str, force: bool = False) -> Snapshot:
        """Replace what the database holds with a snapshot, after taking a
        snapshot of what it holds now.

        Parameters
        ----------
        name: str
            The snapshot to restore.
        force: bool = False
            End the other sessions on a Postgres database rather than refuse
            while there are any.

        Returns
        -------
        Snapshot
            The snapshot taken of what the database held before.

        Raises
        ------
        ValueError
            If there is no such snapshot, it is of another kind of database,
            or other sessions are connected and `force` is not given.
        """
        snapshot = self.get(name)
        if snapshot.dialect != self.dialect:
            raise ValueError(
                f"Snapshot {name} is of a {snapshot.dialect} database, not "
                f"{self.dialect}."
            )
        if self.dialect == "postgresql":
            self._assert_alone(force)
        before = self.create(f"before-restore-of-{name}")
        path = self._folder / snapshot.file
        if self.dialect == "postgresql":
            self._run(
                [
                    "pg_restore",
                    "--clean",
                    "--if-exists",
                    "--no-owner",
                    "--single-transaction",
                    f"--dbname={self._libpq_uri()}",
                    str(path),
                ]
            )
        else:
            self._copy_sqlite(path, self._sqlite_path())
        return before

    def prune(self, keep: int) -> list[Snapshot]:
        """Remove all but the newest snapshots.

        Parameters
        ----------
        keep: int
            How many of the newest to keep, at least one.

        Returns
        -------
        list[Snapshot]
            The snapshots removed.
        """
        if keep < 1:
            raise ValueError("Keep at least one snapshot.")
        removed = self.all()[:-keep]
        for snapshot in removed:
            (self._folder / snapshot.file).unlink(missing_ok=True)
            self._metadata_path(snapshot.name).unlink(missing_ok=True)
        return removed

    @staticmethod
    def sqlalchemy_uri(uri: str) -> str:
        """The URL with the driver the app connects with, psycopg, as
        `DatabaseService` and the migrations rewrite it: a plain
        ``postgresql://`` would have SQLAlchemy look for psycopg2, which is not
        installed."""
        for scheme in ("postgresql://", "postgres://", "postgresql+psycopg2://"):
            if uri.startswith(scheme):
                return "postgresql+psycopg://" + uri[len(scheme) :]
        return uri

    @staticmethod
    def slug(label: str) -> str:
        """A label as it goes into a file name: lower case, with anything
        but letters, digits and dashes made a dash."""
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        return slug or "manual"

    def _metadata_path(self, name: str) -> Path:
        return self._folder / f"{name}.json"

    def _revision(self) -> str | None:
        """The migration revision the database is at, None where it has
        none."""
        engine = create_engine(self._url)
        try:
            with engine.connect() as connection:
                return MigrationContext.configure(connection).get_current_revision()
        finally:
            engine.dispose()

    def _assert_alone(self, force: bool) -> None:
        """Refuse a restore while other sessions are connected to the
        database, or with `force` end them."""
        engine = create_engine(self._url)
        try:
            with engine.connect() as connection:
                others = connection.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE datname = current_database() "
                        "AND pid <> pg_backend_pid()"
                    )
                ).scalar_one()
                if others and not force:
                    raise ValueError(
                        f"{others} other session(s) are connected to the "
                        "database. Stop the app and the worker first, or pass "
                        "--force to end the sessions."
                    )
                if others:
                    connection.execute(
                        text(
                            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                            "WHERE datname = current_database() "
                            "AND pid <> pg_backend_pid()"
                        )
                    )
        finally:
            engine.dispose()

    def _libpq_uri(self) -> str:
        """The URL as the Postgres tools read it: without the driver of the
        app, and without the password, which they are given apart."""
        url: URL = self._url.set(drivername="postgresql", password=None)
        return url.render_as_string(hide_password=False)

    def _run(self, arguments: Sequence[str]) -> None:
        """Run a Postgres tool, with the password in its environment rather
        than in its arguments, where every process could read it."""
        if shutil.which(arguments[0]) is None:
            raise RuntimeError(
                f"{arguments[0]} is not installed. Snapshots of a Postgres "
                "database need the Postgres client tools, of the server's "
                "version or newer."
            )
        environment = dict(os.environ)
        if self._url.password is not None:
            environment["PGPASSWORD"] = str(self._url.password)
        result = subprocess.run(  # noqa: S603
            arguments, env=environment, capture_output=True, text=True
        )
        if result.returncode != 0:
            output = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"{arguments[0]} failed: {output}")

    def _sqlite_path(self) -> Path:
        if not self._url.database or self._url.database == ":memory:":
            raise ValueError("An in-memory SQLite database cannot be snapshot.")
        return Path(self._url.database)

    @staticmethod
    def _copy_sqlite(source: Path, target: Path) -> None:
        """Copy a SQLite database with SQLite's own backup, which is
        consistent while it is in use."""
        with (
            closing(sqlite3.connect(source)) as from_connection,
            closing(sqlite3.connect(target)) as to_connection,
        ):
            from_connection.backup(to_connection)
