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

pytestmark = pytest.mark.unittest


def enum_column(name: str) -> sa.ColumnClause:
    """A column of an enum type, left untyped so that Postgres reads a value
    written to it as the enum of the column rather than as a string."""
    return sa.column(name)


def insert_dataset(session: Session) -> UUID:
    """Store a dataset, with the columns it has had since the baseline, for a
    row that refers to one."""
    dataset = sa.table(
        "dataset",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("schema_uid", sa.Uuid()),
    )
    dataset_uid = uuid4()
    session.execute(
        sa.insert(dataset).values(uid=dataset_uid, name="dataset", schema_uid=uuid4())
    )
    return dataset_uid


def insert_batch(session: Session, dataset_uid: UUID) -> UUID:
    """Store a batch in a project of its own, with the columns they have had
    since the baseline, for an item that refers to one."""
    project = sa.table(
        "project",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        enum_column("status"),
        sa.column("locked", sa.Boolean()),
        sa.column("root_schema_uid", sa.Uuid()),
        sa.column("schema_uid", sa.Uuid()),
        sa.column("created", sa.DateTime()),
        sa.column("dataset_uid", sa.Uuid()),
    )
    batch = sa.table(
        "batch",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        enum_column("status"),
        sa.column("created", sa.DateTime()),
        sa.column("project_uid", sa.Uuid()),
    )
    project_uid, batch_uid = uuid4(), uuid4()
    created = datetime.datetime(2026, 1, 1)
    session.execute(
        sa.insert(project).values(
            uid=project_uid,
            name="project",
            status="IN_PROGRESS",
            locked=False,
            root_schema_uid=uuid4(),
            schema_uid=uuid4(),
            created=created,
            dataset_uid=dataset_uid,
        )
    )
    session.execute(
        sa.insert(batch).values(
            uid=batch_uid,
            name="batch",
            status="INITIALIZED",
            created=created,
            project_uid=project_uid,
        )
    )
    return batch_uid


ITEM = sa.table(
    "item",
    sa.column("uid", sa.Uuid()),
    sa.column("identifier", sa.String()),
    sa.column("selected", sa.Boolean()),
    sa.column("valid_attributes", sa.Boolean()),
    sa.column("valid_relations", sa.Boolean()),
    sa.column("valid_pseudonym", sa.Boolean()),
    sa.column("locked", sa.Boolean()),
    enum_column("item_value_type"),
    enum_column("review_status"),
    sa.column("schema_uid", sa.Uuid()),
    sa.column("dataset_uid", sa.Uuid()),
    sa.column("batch_uid", sa.Uuid()),
)


def item_row(
    uid: UUID,
    identifier: str,
    dataset_uid: UUID,
    batch_uid: UUID,
    selected: bool = True,
    item_value_type: str = "SAMPLE",
) -> dict:
    return {
        "uid": uid,
        "identifier": identifier,
        "selected": selected,
        "valid_attributes": True,
        "valid_relations": True,
        "valid_pseudonym": True,
        "locked": False,
        "item_value_type": item_value_type,
        "review_status": "NOT_REVIEWED",
        "schema_uid": uuid4(),
        "dataset_uid": dataset_uid,
        "batch_uid": batch_uid,
    }


def insert_item(session: Session) -> UUID:
    """Store a sample in a dataset and batch of its own, for a row that refers
    to an item."""
    dataset_uid = insert_dataset(session)
    batch_uid = insert_batch(session, dataset_uid)
    item_uid = uuid4()
    session.execute(
        sa.insert(ITEM), [item_row(item_uid, "item", dataset_uid, batch_uid)]
    )
    return item_uid


@pytest.fixture
def session(empty_database_uri: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SLIDETAP_DBURI", empty_database_uri)
    database_service = DatabaseService(DatabaseConfig(empty_database_uri, False))
    with database_service.get_session() as session:
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
    dataset_uid = insert_dataset(session)
    batch_uid = insert_batch(session, dataset_uid)

    session.execute(
        sa.insert(ITEM),
        [
            item_row(
                uids[name],
                name,
                dataset_uid,
                batch_uid,
                selected=name in selected,
                item_value_type=value_types.get(name, "SAMPLE"),
            )
            for name in uids
        ],
    )
    sample = sa.table("sample", sa.column("uid", sa.Uuid()))
    image = sa.table(
        "image",
        sa.column("uid", sa.Uuid()),
        enum_column("status"),
        enum_column("format"),
    )
    session.execute(
        sa.insert(sample),
        [{"uid": uids[name]} for name in uids if name not in value_types],
    )
    session.execute(
        sa.insert(image),
        [
            {
                "uid": uids["image_under_out"],
                "status": "NOT_STARTED",
                "format": "DICOM_WSI",
            }
        ],
    )
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
        enum_column("status"),
        sa.column("root_schema_uid", sa.Uuid()),
        sa.column("schema_uid", sa.Uuid()),
        sa.column("dataset_uid", sa.Uuid()),
        sa.column("created", sa.DateTime()),
        sa.column("valid_attributes", sa.Boolean()),
        sa.column("locked", sa.Boolean()),
    )
    uid = uuid4()
    dataset_uid = insert_dataset(session)
    session.execute(
        sa.insert(project),
        [
            {
                "uid": uid,
                "name": "project",
                "status": "COMPLETED",
                "root_schema_uid": uuid4(),
                "schema_uid": uuid4(),
                "dataset_uid": dataset_uid,
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
        enum_column("status"),
        sa.column("root_schema_uid", sa.Uuid()),
        sa.column("schema_uid", sa.Uuid()),
        sa.column("dataset_uid", sa.Uuid()),
        sa.column("created", sa.DateTime()),
        sa.column("valid_attributes", sa.Boolean()),
        sa.column("locked", sa.Boolean()),
    )
    uids = {status: uuid4() for status in ("EXPORT_COMPLETE", "IN_PROGRESS")}
    dataset_uid = insert_dataset(session)
    session.execute(
        sa.insert(project),
        [
            {
                "uid": uid,
                "name": status,
                "status": status,
                "root_schema_uid": uuid4(),
                "schema_uid": uuid4(),
                "dataset_uid": dataset_uid,
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
        enum_column("status"),
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
        sa.column("previous_project_status", sa.String()),
        enum_column("status"),
        sa.column("created", sa.DateTime()),
        sa.column("updated", sa.DateTime()),
    )
    migration_entity = sa.table(
        "migration_entity",
        sa.column("uid", sa.Uuid()),
        sa.column("migration_uid", sa.Uuid()),
        sa.column("entity_uid", sa.Uuid()),
        sa.column("target_entity_schema_uid", sa.Uuid()),
        sa.column("identifier", sa.String()),
        sa.column("position", sa.Integer()),
    )
    issue = sa.table(
        "attribute_migration_issue",
        sa.column("uid", sa.Uuid()),
        sa.column("migration_entity_uid", sa.Uuid()),
        sa.column("source_attribute_schema_uid", sa.Uuid()),
        sa.column("target_attribute_schema_uid", sa.Uuid()),
        sa.column("original", sa.JSON()),
        sa.column("problem", sa.String()),
    )
    uids = {status: uuid4() for status in ("MIGRATING", "IN_PROGRESS")}
    created = datetime.datetime(2026, 1, 1)
    dataset_uid = insert_dataset(session)
    session.execute(
        sa.insert(project),
        [
            {
                "uid": uid,
                "name": status,
                "status": status,
                "root_schema_uid": uuid4(),
                "schema_uid": uuid4(),
                "dataset_uid": dataset_uid,
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
                "previous_project_status": "COMPLETED",
                "status": "CURATING",
                "created": created,
                "updated": created,
            }
        ],
    )
    migration_entity_uid = uuid4()
    session.execute(
        sa.insert(migration_entity),
        [
            {
                "uid": migration_entity_uid,
                "migration_uid": migration_uid,
                "entity_uid": uids["MIGRATING"],
                "target_entity_schema_uid": uuid4(),
                "identifier": "MIGRATING",
                "position": 0,
            }
        ],
    )
    session.execute(
        sa.insert(issue),
        [
            {
                "uid": uuid4(),
                "migration_entity_uid": migration_entity_uid,
                "source_attribute_schema_uid": uuid4(),
                "target_attribute_schema_uid": uuid4(),
                "original": {"attributeValueType": "enum"},
                "problem": "no counterpart",
            },
            {
                "uid": uuid4(),
                "migration_entity_uid": migration_entity_uid,
                "source_attribute_schema_uid": uuid4(),
                "target_attribute_schema_uid": None,
                "original": {"attributeValueType": "string"},
                "problem": "dropped",
            },
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
    assert "migration_entity" not in tables
    assert "attribute_migration_issue" not in tables
    command.upgrade(config(), "head")
    assert_up_to_date(session)


MIGRATION_ENTITY = sa.table(
    "migration_entity",
    sa.column("uid", sa.Uuid()),
    sa.column("migration_uid", sa.Uuid()),
    sa.column("entity_uid", sa.Uuid()),
    sa.column("target_entity_schema_uid", sa.Uuid()),
    sa.column("identifier", sa.String()),
    sa.column("position", sa.Integer()),
)


@pytest.fixture
def migration_uid(session: Session) -> UUID:
    """The uid of the migration of a project, in a database at head."""
    command.upgrade(config(), "head")
    project = sa.table(
        "project",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        enum_column("status"),
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
        sa.column("previous_project_status", sa.String()),
        enum_column("status"),
        sa.column("created", sa.DateTime()),
        sa.column("updated", sa.DateTime()),
    )
    project_uid = uuid4()
    created = datetime.datetime(2026, 1, 1)
    dataset_uid = insert_dataset(session)
    session.execute(
        sa.insert(project),
        [
            {
                "uid": project_uid,
                "name": "project",
                "status": "MIGRATING",
                "root_schema_uid": uuid4(),
                "schema_uid": uuid4(),
                "dataset_uid": dataset_uid,
                "created": created,
                "valid_attributes": True,
                "locked": False,
            }
        ],
    )
    migration_uid = uuid4()
    session.execute(
        sa.insert(migration),
        [
            {
                "uid": migration_uid,
                "project_uid": project_uid,
                "source_root_schema_uid": uuid4(),
                "target_root_schema_uid": uuid4(),
                "previous_project_status": "IN_PROGRESS",
                "status": "CURATING",
                "created": created,
                "updated": created,
            }
        ],
    )
    session.commit()
    return migration_uid


def test_an_entity_is_in_a_migration_once(session: Session, migration_uid: UUID):
    entity_uid = uuid4()

    def row(position: int) -> dict:
        return {
            "uid": uuid4(),
            "migration_uid": migration_uid,
            "entity_uid": entity_uid,
            "target_entity_schema_uid": uuid4(),
            "identifier": "item",
            "position": position,
        }

    session.execute(sa.insert(MIGRATION_ENTITY), [row(0)])
    session.commit()

    with pytest.raises(sa.exc.IntegrityError):
        session.execute(sa.insert(MIGRATION_ENTITY), [row(1)])
        session.commit()
    session.rollback()


def test_an_attribute_issue_of_an_entity_is_unique(
    session: Session, migration_uid: UUID
):
    """An attribute issue of an entity is unique by its target attribute
    schema, or, for a dropped attribute, its source attribute schema; an issue
    has one of them."""
    issue = sa.table(
        "attribute_migration_issue",
        sa.column("uid", sa.Uuid()),
        sa.column("migration_entity_uid", sa.Uuid()),
        sa.column("source_attribute_schema_uid", sa.Uuid()),
        sa.column("target_attribute_schema_uid", sa.Uuid()),
        sa.column("problem", sa.String()),
    )
    migration_entity_uid = uuid4()
    session.execute(
        sa.insert(MIGRATION_ENTITY),
        [
            {
                "uid": migration_entity_uid,
                "migration_uid": migration_uid,
                "entity_uid": uuid4(),
                "target_entity_schema_uid": uuid4(),
                "identifier": "project",
                "position": 0,
            }
        ],
    )
    source_attribute_schema_uid = uuid4()
    target_attribute_schema_uid = uuid4()

    def row(
        source: UUID | None = source_attribute_schema_uid,
        target: UUID | None = target_attribute_schema_uid,
    ) -> dict:
        return {
            "uid": uuid4(),
            "migration_entity_uid": migration_entity_uid,
            "source_attribute_schema_uid": source,
            "target_attribute_schema_uid": target,
            "problem": "no counterpart",
        }

    # An issue with a target, and a dropped attribute of the same source.
    session.execute(sa.insert(issue), [row(), row(target=None)])
    session.commit()

    for duplicate in (
        row(source=uuid4()),
        row(source=None),
        row(target=None),
        row(source=None, target=None),
    ):
        with pytest.raises(sa.exc.IntegrityError):
            session.execute(sa.insert(issue), [duplicate])
            session.commit()
        session.rollback()


UNIQUE_ATTRIBUTE_REVISION = "3c8e51f7a2d4"

attribute_table = sa.table(
    "attribute",
    sa.column("uid", sa.Uuid()),
    sa.column("schema_uid", sa.Uuid()),
    sa.column("valid", sa.Boolean()),
    sa.column("tag", sa.String()),
    enum_column("attribute_value_type"),
    sa.column("read_only", sa.Boolean()),
    sa.column("locked", sa.Boolean()),
    sa.column("attribute_item_uid", sa.Uuid()),
)


def attribute_row(schema_uid: UUID, item_uid: UUID) -> dict:
    return {
        "uid": uuid4(),
        "schema_uid": schema_uid,
        "valid": True,
        "tag": "tag",
        "attribute_value_type": "STRING",
        "read_only": False,
        "locked": False,
        "attribute_item_uid": item_uid,
    }


def upgrade_to_before(revision: str) -> None:
    before = ScriptDirectory.from_config(config()).get_revision(revision)
    assert before is not None and isinstance(before.down_revision, str)
    command.upgrade(config(), before.down_revision)


def test_an_item_holds_one_attribute_of_a_schema_after_upgrade(session: Session):
    """The constraint before the upgrade let an item hold two attributes of a
    schema, as the other owner columns of the rows are null."""
    upgrade_to_before(UNIQUE_ATTRIBUTE_REVISION)
    schema_uid, item_uid = uuid4(), insert_item(session)
    session.execute(
        sa.insert(attribute_table),
        [attribute_row(schema_uid, item_uid), attribute_row(uuid4(), item_uid)],
    )
    session.commit()

    command.upgrade(config(), "head")

    with pytest.raises(sa.exc.IntegrityError):
        session.execute(
            sa.insert(attribute_table), [attribute_row(schema_uid, item_uid)]
        )
        session.commit()


def test_an_upgrade_stops_on_an_item_holding_two_attributes_of_a_schema(
    session: Session,
):
    upgrade_to_before(UNIQUE_ATTRIBUTE_REVISION)
    schema_uid, item_uid = uuid4(), insert_item(session)
    session.execute(
        sa.insert(attribute_table),
        [attribute_row(schema_uid, item_uid), attribute_row(schema_uid, item_uid)],
    )
    session.commit()

    # SQLite holds a uid as its hex and Postgres as a uuid, and the report
    # reads back what the database holds.
    with pytest.raises(
        RuntimeError, match=f"attribute_item_uid ({item_uid.hex}|{item_uid})"
    ):
        command.upgrade(config(), "head")


def test_an_upgrade_stops_on_mappers_without_a_family_sharing_a_name(
    session: Session,
):
    upgrade_to_before(UNIQUE_ATTRIBUTE_REVISION)
    mapper = sa.table(
        "mapper",
        sa.column("uid", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("attribute_schema_uid", sa.Uuid()),
        sa.column("root_attribute_schema_uid", sa.Uuid()),
    )
    session.execute(
        sa.insert(mapper),
        [
            {
                "uid": uuid4(),
                "name": "Sex",
                "attribute_schema_uid": uuid4(),
                "root_attribute_schema_uid": uuid4(),
            }
            for _ in range(2)
        ],
    )
    session.commit()

    with pytest.raises(RuntimeError, match="mapper name 'Sex' without family"):
        command.upgrade(config(), "head")


def test_a_mapper_keeps_its_lowest_group_on_downgrade_to_one_group(
    session: Session,
):
    """The column a mapper's group goes back to holds one group, so of the
    groups it is in, the one with the lowest uid is kept."""
    command.upgrade(config(), "b4e2f7c81a95")
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
    )
    join_table = sa.table(
        "mapper_to_mapper_group",
        sa.column("mapper_uid", sa.Uuid()),
        sa.column("mapper_group_uid", sa.Uuid()),
    )
    lowest_group_uid = UUID("00000000-0000-4000-8000-000000000001")
    highest_group_uid = UUID("ffffffff-0000-4000-8000-000000000001")
    mapper_uid = uuid4()
    session.execute(
        sa.insert(mapper_group),
        [
            {"uid": group_uid, "name": str(group_uid), "default_enabled": False}
            for group_uid in (highest_group_uid, lowest_group_uid)
        ],
    )
    session.execute(
        sa.insert(mapper),
        [
            {
                "uid": mapper_uid,
                "name": "Diagnose",
                "attribute_schema_uid": uuid4(),
                "root_attribute_schema_uid": uuid4(),
            }
        ],
    )
    session.execute(
        sa.insert(join_table),
        [
            {"mapper_uid": mapper_uid, "mapper_group_uid": group_uid}
            for group_uid in (highest_group_uid, lowest_group_uid)
        ],
    )
    session.commit()

    command.downgrade(config(), "70048a43fda6")

    single_group = sa.table(
        "mapper",
        sa.column("uid", sa.Uuid()),
        sa.column("mapper_group_uid", sa.Uuid()),
    )
    assert session.execute(
        sa.select(single_group.c.uid, single_group.c.mapper_group_uid)
    ).all() == [(mapper_uid, lowest_group_uid)]
