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

import json
import os
import re
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from click.testing import CliRunner
from sqlalchemy.engine import make_url
from typer.main import get_command

from slidetap.migrations.cli import app
from slidetap.migrations.snapshot import DatabaseSnapshots

pytestmark = pytest.mark.unittest


@pytest.fixture()
def db_uri(tmp_path: Path) -> str:
    """A SQLite database at a revision, holding one row."""
    uri = f"sqlite:///{tmp_path / 'slidetap.db'}"
    engine = sa.create_engine(uri)
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE alembic_version (version_num TEXT)"))
        connection.execute(sa.text("INSERT INTO alembic_version VALUES ('abc123')"))
        connection.execute(sa.text("CREATE TABLE item (name TEXT)"))
        connection.execute(sa.text("INSERT INTO item VALUES ('before')"))
    engine.dispose()
    return uri


@pytest.fixture()
def snapshots(db_uri: str, tmp_path: Path) -> DatabaseSnapshots:
    return DatabaseSnapshots(db_uri, tmp_path / "snapshots")


def names(db_uri: str) -> list[str]:
    engine = sa.create_engine(db_uri)
    try:
        with engine.connect() as connection:
            return list(connection.execute(sa.text("SELECT name FROM item")).scalars())
    finally:
        engine.dispose()


def write(db_uri: str, statement: str) -> None:
    engine = sa.create_engine(db_uri)
    try:
        with engine.begin() as connection:
            connection.execute(sa.text(statement))
    finally:
        engine.dispose()


class TestDatabaseSnapshots:
    def test_create_writes_the_snapshot_and_what_it_is(
        self, snapshots: DatabaseSnapshots
    ):
        # Act
        snapshot = snapshots.create("Before remap!")

        # Assert
        assert snapshot.name.endswith("-before-remap")
        assert snapshot.revision == "abc123"
        assert snapshot.dialect == "sqlite"
        assert (snapshots.folder / snapshot.file).stat().st_size == snapshot.size
        metadata = json.loads(
            (snapshots.folder / f"{snapshot.name}.json").read_text(encoding="utf-8")
        )
        assert metadata["label"] == "Before remap!"

    def test_snapshots_taken_in_one_second_have_names_of_their_own(
        self, snapshots: DatabaseSnapshots
    ):
        # Act
        first = snapshots.create("deploy")
        second = snapshots.create("deploy")

        # Assert
        assert first.name != second.name
        assert [snapshot.name for snapshot in snapshots.all()] == [
            first.name,
            second.name,
        ]

    def test_restore_puts_back_what_the_snapshot_holds(
        self, snapshots: DatabaseSnapshots, db_uri: str
    ):
        # Arrange
        snapshot = snapshots.create("deploy")
        write(db_uri, "UPDATE item SET name = 'after'")

        # Act
        before = snapshots.restore(snapshot.name)

        # Assert
        assert names(db_uri) == ["before"]
        assert before.label == f"before-restore-of-{snapshot.name}"

    def test_a_restore_can_be_undone(self, snapshots: DatabaseSnapshots, db_uri: str):
        # Arrange
        snapshot = snapshots.create("deploy")
        write(db_uri, "UPDATE item SET name = 'after'")
        before = snapshots.restore(snapshot.name)

        # Act
        snapshots.restore(before.name)

        # Assert
        assert names(db_uri) == ["after"]

    def test_restore_refuses_a_snapshot_of_another_kind_of_database(
        self, snapshots: DatabaseSnapshots
    ):
        # Arrange
        snapshot = snapshots.create("deploy")
        path = snapshots.folder / f"{snapshot.name}.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**metadata, "dialect": "postgresql"}))

        # Act & Assert
        with pytest.raises(ValueError, match="postgresql"):
            snapshots.restore(snapshot.name)

    def test_restore_refuses_a_snapshot_that_is_not_there(
        self, snapshots: DatabaseSnapshots
    ):
        # Act & Assert
        with pytest.raises(ValueError, match="No snapshot"):
            snapshots.restore("20260101-000000-missing")

    def test_prune_keeps_the_newest(self, snapshots: DatabaseSnapshots):
        # Arrange
        taken = [snapshots.create(f"deploy {number}") for number in range(4)]

        # Act
        removed = snapshots.prune(keep=2)

        # Assert
        assert [snapshot.name for snapshot in removed] == [
            snapshot.name for snapshot in taken[:2]
        ]
        assert [snapshot.name for snapshot in snapshots.all()] == [
            snapshot.name for snapshot in taken[2:]
        ]
        assert sorted(path.name for path in snapshots.folder.iterdir()) == sorted(
            name
            for snapshot in taken[2:]
            for name in (snapshot.file, f"{snapshot.name}.json")
        )

    def test_prune_keeps_at_least_one(self, snapshots: DatabaseSnapshots):
        # Act & Assert
        with pytest.raises(ValueError):
            snapshots.prune(keep=0)

    def test_no_folder_lists_no_snapshots(self, snapshots: DatabaseSnapshots):
        # Act & Assert
        assert snapshots.all() == []

    def test_a_database_of_another_kind_is_refused(self, tmp_path: Path):
        # Act & Assert
        with pytest.raises(ValueError, match="mysql"):
            DatabaseSnapshots("mysql://user@localhost/slidetap", tmp_path)


class TestSqlalchemyUri:
    @pytest.mark.parametrize(
        "uri",
        [
            "postgresql://user:secret@db:5432/slidetap",
            "postgres://user:secret@db:5432/slidetap",
            "postgresql+psycopg2://user:secret@db:5432/slidetap",
        ],
    )
    def test_connects_with_psycopg(self, uri: str):
        # Act
        rewritten = DatabaseSnapshots.sqlalchemy_uri(uri)

        # Assert
        assert rewritten == "postgresql+psycopg://user:secret@db:5432/slidetap"

    def test_leaves_sqlite_as_it_is(self):
        # Act & Assert
        assert DatabaseSnapshots.sqlalchemy_uri("sqlite:///x.db") == "sqlite:///x.db"


class TestSnapshotFolder:
    def test_is_the_one_named(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        # Arrange
        monkeypatch.setenv("SLIDETAP_SNAPSHOTS", str(tmp_path / "named"))
        monkeypatch.setenv("SLIDETAP_STORAGE", str(tmp_path / "storage"))

        # Act & Assert
        assert DatabaseSnapshots.folder_from_environment() == tmp_path / "named"

    def test_is_else_in_the_storage(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        # Arrange
        monkeypatch.delenv("SLIDETAP_SNAPSHOTS", raising=False)
        monkeypatch.setenv("SLIDETAP_STORAGE", str(tmp_path))

        # Act & Assert
        assert DatabaseSnapshots.folder_from_environment() == tmp_path / "snapshots"

    def test_is_refused_where_neither_is_set(self, monkeypatch: pytest.MonkeyPatch):
        # Arrange
        monkeypatch.delenv("SLIDETAP_SNAPSHOTS", raising=False)
        monkeypatch.delenv("SLIDETAP_STORAGE", raising=False)

        # Act & Assert
        with pytest.raises(ValueError, match="SLIDETAP_SNAPSHOTS"):
            DatabaseSnapshots.folder_from_environment()


class TestSnapshotCommands:
    def test_create_list_restore_and_prune(self, db_uri: str, tmp_path: Path):
        # Arrange
        runner = CliRunner()
        command = get_command(app)
        options = ["--db-uri", db_uri, "--folder", str(tmp_path / "snapshots")]

        # Act
        created = runner.invoke(
            command, ["snapshot", "create", "--label", "deploy", *options]
        )
        found = re.search(r"Snapshot (\S+) taken", created.output)
        assert found, created.output
        name = found.group(1)
        write(db_uri, "UPDATE item SET name = 'after'")
        restored = runner.invoke(command, ["snapshot", "restore", name, *options])
        listed = runner.invoke(command, ["snapshot", "list", *options])
        pruned = runner.invoke(command, ["snapshot", "prune", "--keep", "1", *options])

        # Assert
        assert created.exit_code == 0, created.output
        assert restored.exit_code == 0, restored.output
        assert names(db_uri) == ["before"]
        assert name in listed.output and "before-restore-of" in listed.output
        assert pruned.exit_code == 0 and "Removed 1" in pruned.output


@pytest.mark.skipif(
    not os.environ.get("SLIDETAP_TEST_DBURI") or shutil.which("pg_dump") is None,
    reason="Needs a Postgres server in SLIDETAP_TEST_DBURI and the Postgres tools.",
)
def test_a_postgres_database_is_snapshot_and_restored(tmp_path: Path):
    # Arrange: a database of its own on the test server.
    server = make_url(os.environ["SLIDETAP_TEST_DBURI"]).set(
        drivername="postgresql+psycopg"
    )
    database = f"slidetap_snapshot_{uuid4().hex}"
    admin = sa.create_engine(server, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{database}"'))
    db_uri = server.set(database=database).render_as_string(hide_password=False)
    try:
        write(db_uri, "CREATE TABLE item (name TEXT)")
        write(db_uri, "INSERT INTO item VALUES ('before')")
        snapshots = DatabaseSnapshots(db_uri, tmp_path)
        snapshot = snapshots.create("deploy")
        write(db_uri, "UPDATE item SET name = 'after'")

        # Act
        snapshots.restore(snapshot.name)

        # Assert
        assert snapshot.file.endswith(".dump")
        assert names(db_uri) == ["before"]
    finally:
        with admin.connect() as connection:
            connection.execute(
                sa.text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
            )
        admin.dispose()
