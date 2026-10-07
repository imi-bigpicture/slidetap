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

import datetime
from pathlib import Path
from uuid import UUID, uuid4

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


def test_mapper_names_are_unique_within_a_family_after_upgrade(session: Session):
    """A mapper is found by its name within the family of its root, so two of
    a name are refused in one family and allowed in two."""
    command.upgrade(config(), "head")
    mapper = sa.table(
        "mapper",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("attribute_schema_uid", sa.Uuid()),
        sa.column("root_attribute_schema_uid", sa.Uuid()),
        sa.column("family_uid", sa.Uuid()),
    )

    def row(family_uid: UUID) -> dict:
        schema_uid = uuid4()
        return {
            "uid": uuid4(),
            "name": "Sex",
            "attribute_schema_uid": schema_uid,
            "root_attribute_schema_uid": schema_uid,
            "family_uid": family_uid,
        }

    family_uid = uuid4()
    session.execute(sa.insert(mapper), [row(family_uid), row(uuid4())])
    session.commit()

    with pytest.raises(sa.exc.IntegrityError):
        session.execute(sa.insert(mapper), [row(family_uid)])
        session.commit()


def test_a_project_can_be_migrating_after_upgrade(session: Session):
    """The status a project is in while it is moved to another root schema,
    which the column did not hold before."""
    migrating_revision = "9e4b7c2d1a63"
    before = ScriptDirectory.from_config(config()).get_revision(migrating_revision)
    assert before is not None and isinstance(before.down_revision, str)
    command.upgrade(config(), before.down_revision)
    project = sa.table(
        "project",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("status", sa.String()),
        sa.column("root_schema_uid", sa.Uuid()),
        sa.column("schema_uid", sa.Uuid()),
        sa.column("dataset_uid", sa.Uuid()),
        sa.column("created", sa.DateTime()),
        sa.column("valid_attributes", sa.Boolean()),
        sa.column("locked", sa.Boolean()),
    )
    uid = uuid4()
    session.execute(
        sa.insert(project),
        [
            {
                "uid": uid,
                "name": "project",
                "status": "COMPLETED",
                "root_schema_uid": uuid4(),
                "schema_uid": uuid4(),
                "dataset_uid": uuid4(),
                "created": datetime.datetime(2026, 1, 1),
                "valid_attributes": True,
                "locked": False,
            }
        ],
    )
    session.commit()

    command.upgrade(config(), migrating_revision)
    session.execute(
        sa.update(project).where(project.c.uid == uid).values(status="MIGRATING")
    )
    session.commit()

    assert session.execute(
        sa.select(project.c.name, project.c.status).where(project.c.uid == uid)
    ).one() == ("project", "MIGRATING")


def test_projects_whose_export_is_complete_are_exported_after_upgrade(
    session: Session,
):
    """When they were exported is not known, but that they were is."""
    exported_revision = "2f8a6d4c9b17"
    before = ScriptDirectory.from_config(config()).get_revision(exported_revision)
    assert before is not None and isinstance(before.down_revision, str)
    command.upgrade(config(), before.down_revision)
    project = sa.table(
        "project",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("status", sa.String()),
        sa.column("root_schema_uid", sa.Uuid()),
        sa.column("schema_uid", sa.Uuid()),
        sa.column("dataset_uid", sa.Uuid()),
        sa.column("created", sa.DateTime()),
        sa.column("valid_attributes", sa.Boolean()),
        sa.column("locked", sa.Boolean()),
    )
    uids = {status: uuid4() for status in ("EXPORT_COMPLETE", "IN_PROGRESS")}
    session.execute(
        sa.insert(project),
        [
            {
                "uid": uid,
                "name": status,
                "status": status,
                "root_schema_uid": uuid4(),
                "schema_uid": uuid4(),
                "dataset_uid": uuid4(),
                "created": datetime.datetime(2026, 1, 1),
                "valid_attributes": True,
                "locked": False,
            }
            for status, uid in uids.items()
        ],
    )
    session.commit()

    command.upgrade(config(), exported_revision)

    exported = sa.table(
        "project", sa.column("name", sa.String()), sa.column("exported", sa.DateTime())
    )
    assert {
        name: when is not None
        for name, when in session.execute(sa.select(exported)).all()
    } == {"EXPORT_COMPLETE": True, "IN_PROGRESS": False}


def test_a_project_being_migrated_gets_its_status_back_on_downgrade(
    session: Session,
):
    """The migration tables are dropped, and a project left migrating by them
    is as it was before the migration, with the status it had."""
    migration_revision = "4d2a7f91c3e8"
    before = ScriptDirectory.from_config(config()).get_revision(migration_revision)
    assert before is not None and isinstance(before.down_revision, str)
    command.upgrade(config(), migration_revision)
    project = sa.table(
        "project",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("status", sa.String()),
        sa.column("root_schema_uid", sa.Uuid()),
        sa.column("schema_uid", sa.Uuid()),
        sa.column("dataset_uid", sa.Uuid()),
        sa.column("created", sa.DateTime()),
        sa.column("valid_attributes", sa.Boolean()),
        sa.column("locked", sa.Boolean()),
    )
    migration = sa.table(
        "project_migration",
        sa.column("uid", sa.Uuid()),
        sa.column("project_uid", sa.Uuid()),
        sa.column("source_root_schema_uid", sa.Uuid()),
        sa.column("target_root_schema_uid", sa.Uuid()),
        sa.column("previous_status", sa.String()),
        sa.column("state", sa.String()),
        sa.column("created", sa.DateTime()),
        sa.column("updated", sa.DateTime()),
    )
    issue = sa.table(
        "migration_attribute_issue",
        sa.column("uid", sa.Uuid()),
        sa.column("migration_uid", sa.Uuid()),
        sa.column("item_uid", sa.Uuid()),
        sa.column("object_schema_uid", sa.Uuid()),
        sa.column("attribute_schema_uid", sa.Uuid()),
        sa.column("original", sa.JSON()),
        sa.column("reason", sa.String()),
        sa.column("decided", sa.Boolean()),
    )
    dropped = sa.table(
        "migration_dropped_attribute",
        sa.column("uid", sa.Uuid()),
        sa.column("migration_uid", sa.Uuid()),
        sa.column("item_uid", sa.Uuid()),
        sa.column("object_schema_uid", sa.Uuid()),
        sa.column("attribute_schema_uid", sa.Uuid()),
        sa.column("original", sa.JSON()),
    )
    uids = {status: uuid4() for status in ("MIGRATING", "IN_PROGRESS")}
    created = datetime.datetime(2026, 1, 1)
    session.execute(
        sa.insert(project),
        [
            {
                "uid": uid,
                "name": status,
                "status": status,
                "root_schema_uid": uuid4(),
                "schema_uid": uuid4(),
                "dataset_uid": uuid4(),
                "created": created,
                "valid_attributes": True,
                "locked": False,
            }
            for status, uid in uids.items()
        ],
    )
    migration_uid = uuid4()
    session.execute(
        sa.insert(migration),
        [
            {
                "uid": migration_uid,
                "project_uid": uids["MIGRATING"],
                "source_root_schema_uid": uuid4(),
                "target_root_schema_uid": uuid4(),
                "previous_status": "COMPLETED",
                "state": "CURATING",
                "created": created,
                "updated": created,
            }
        ],
    )
    session.execute(
        sa.insert(issue),
        [
            {
                "uid": uuid4(),
                "migration_uid": migration_uid,
                "item_uid": None,
                "object_schema_uid": uuid4(),
                "attribute_schema_uid": uuid4(),
                "original": {"attributeValueType": "enum"},
                "reason": "no counterpart",
                "decided": False,
            }
        ],
    )
    session.execute(
        sa.insert(dropped),
        [
            {
                "uid": uuid4(),
                "migration_uid": migration_uid,
                "item_uid": None,
                "object_schema_uid": uuid4(),
                "attribute_schema_uid": uuid4(),
                "original": {"attributeValueType": "string"},
            }
        ],
    )
    session.commit()

    command.downgrade(config(), before.down_revision)

    assert {
        name: status
        for name, status in session.execute(
            sa.select(project.c.name, project.c.status)
        ).all()
    } == {"MIGRATING": "COMPLETED", "IN_PROGRESS": "IN_PROGRESS"}
    tables = sa.inspect(session.connection()).get_table_names()
    assert "project_migration" not in tables
    assert "migration_attribute_issue" not in tables
    assert "migration_dropped_attribute" not in tables
    command.upgrade(config(), "head")
    assert_up_to_date(session)
