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

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

# typer.testing.CliRunner mangles the output streams with click 8.4, so the
# commands are invoked through click's runner instead.
from click.testing import CliRunner
from sqlalchemy.orm import Session
from typer.main import get_command

from slidetap.config import DatabaseConfig
from slidetap.migrations.cli import app, assert_up_to_date, config, head_revision
from slidetap.services import DatabaseService


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    uri = f"sqlite:///{tmp_path.joinpath('test.db')}"
    monkeypatch.setenv("SLIDETAP_DBURI", uri)
    with DatabaseService(DatabaseConfig(uri, False)).get_session() as session:
        yield session


def test_config_finds_migrations_without_alembic_ini():
    """The in-code configuration resolves the migrations shipped in the package.

    This is what lets deployments run slidetap-db upgrade from any working
    directory, so it breaks if script_location or the packaged versions/ go
    missing.
    """
    scripts = ScriptDirectory.from_config(config())

    assert scripts.get_current_head() is not None


def test_assert_up_to_date_accepts_upgraded_database(session: Session):
    command.upgrade(config(), "head")

    assert_up_to_date(session)


def test_assert_up_to_date_rejects_unmigrated_database(session: Session):
    with pytest.raises(RuntimeError, match="slidetap-db upgrade"):
        assert_up_to_date(session)


def test_assert_up_to_date_rejects_partially_migrated_database(session: Session):
    command.upgrade(config(), "base+1")

    with pytest.raises(RuntimeError, match=str(head_revision())):
        assert_up_to_date(session)


def test_upgrade_command_migrates_database(session: Session):
    """The `slidetap-db upgrade` command, from parsing to applied migrations."""
    result = CliRunner().invoke(get_command(app), ["upgrade"])

    assert result.exit_code == 0
    assert_up_to_date(session)


def test_stamp_command_records_given_revision(session: Session):
    baseline = "6b3c3c59c3e3"

    result = CliRunner().invoke(get_command(app), ["stamp", baseline])

    assert result.exit_code == 0
    assert (
        MigrationContext.configure(session.connection()).get_current_revision()
        == baseline
    )


def test_mapper_group_membership_moves_to_join_table(session: Session):
    """The many-to-many migration keeps the group each mapper belonged to.

    The membership lived in `mapper.mapper_group_uid`, which the migration
    drops, so a mistake here silently unassigns every mapper from its group
    and stops projects using that group from mapping.
    """
    command.upgrade(config(), "70048a43fda6")
    mapper_group = sa.table(
        "mapper_group",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("default_enabled", sa.Boolean()),
    )
    mapper = sa.table(
        "mapper",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("attribute_schema_uid", sa.Uuid()),
        sa.column("root_attribute_schema_uid", sa.Uuid()),
        sa.column("mapper_group_uid", sa.Uuid()),
    )
    group_uid, mapper_uid, schema_uid = uuid4(), uuid4(), uuid4()
    session.execute(
        sa.insert(mapper_group),
        [{"uid": group_uid, "name": "Base", "default_enabled": False}],
    )
    session.execute(
        sa.insert(mapper),
        [
            {
                "uid": mapper_uid,
                "name": "Diagnose",
                "attribute_schema_uid": schema_uid,
                "root_attribute_schema_uid": schema_uid,
                "mapper_group_uid": group_uid,
            }
        ],
    )
    session.commit()

    command.upgrade(config(), "head")

    join_table = sa.table(
        "mapper_to_mapper_group",
        sa.column("mapper_uid", sa.Uuid()),
        sa.column("mapper_group_uid", sa.Uuid()),
    )
    assert session.execute(sa.select(join_table)).all() == [(mapper_uid, group_uid)]


def test_curator_excluded_is_read_off_what_is_left_out(session: Session):
    """Before the column, nothing recorded why an item was out. The migration
    takes an item that is out under nothing that is out to have been taken out
    by a curator, and one under something out to have gone with it, since the
    difference decides whether a later cascade brings it back."""
    command.upgrade(config(), "d8a4c5f19e6b")
    item = sa.table(
        "item",
        sa.column("uid", sa.Uuid()),
        sa.column("identifier", sa.String()),
        sa.column("selected", sa.Boolean()),
        sa.column("valid_attributes", sa.Boolean()),
        sa.column("valid_relations", sa.Boolean()),
        sa.column("valid_pseudonym", sa.Boolean()),
        sa.column("locked", sa.Boolean()),
        sa.column("item_value_type", sa.String()),
        sa.column("review_status", sa.String()),
        sa.column("schema_uid", sa.Uuid()),
        sa.column("dataset_uid", sa.Uuid()),
        sa.column("batch_uid", sa.Uuid()),
    )
    observation = sa.table(
        "observation", sa.column("uid", sa.Uuid()), sa.column("sample_uid", sa.Uuid())
    )
    sample_to_sample = sa.table(
        "sample_to_sample",
        sa.column("parent_uid", sa.Uuid()),
        sa.column("child_uid", sa.Uuid()),
    )
    sample_to_image = sa.table(
        "sample_to_image",
        sa.column("sample_uid", sa.Uuid()),
        sa.column("image_uid", sa.Uuid()),
    )
    uids = {
        name: uuid4()
        for name in (
            "top_out",
            "under_out",
            "holder_in",
            "under_in",
            "image_under_out",
            "observation_on_in",
            "in",
        )
    }
    value_types = {"image_under_out": "IMAGE", "observation_on_in": "OBSERVATION"}
    selected = {"holder_in", "in"}

    def row(name: str) -> dict:
        return {
            "uid": uids[name],
            "identifier": name,
            "selected": name in selected,
            "valid_attributes": True,
            "valid_relations": True,
            "valid_pseudonym": True,
            "locked": False,
            "item_value_type": value_types.get(name, "SAMPLE"),
            "review_status": "NOT_REVIEWED",
            "schema_uid": uuid4(),
            "dataset_uid": uuid4(),
            "batch_uid": uuid4(),
        }

    session.execute(sa.insert(item), [row(name) for name in uids])
    session.execute(
        sa.insert(sample_to_sample),
        [
            {"parent_uid": uids["top_out"], "child_uid": uids["under_out"]},
            {"parent_uid": uids["holder_in"], "child_uid": uids["under_in"]},
        ],
    )
    session.execute(
        sa.insert(sample_to_image),
        [{"sample_uid": uids["under_out"], "image_uid": uids["image_under_out"]}],
    )
    session.execute(
        sa.insert(observation),
        [{"uid": uids["observation_on_in"], "sample_uid": uids["holder_in"]}],
    )
    session.commit()

    command.upgrade(config(), "head")

    excluded = sa.table(
        "item", sa.column("uid", sa.Uuid()), sa.column("curator_excluded", sa.Boolean())
    )
    marked = {
        uid
        for uid, curator_excluded in session.execute(sa.select(excluded)).all()
        if curator_excluded
    }
    names = {uid: name for name, uid in uids.items()}
    assert {names[uid] for uid in marked} == {
        "top_out",
        "under_in",
        "observation_on_in",
    }
