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

import os
from pathlib import Path

import pytest

# typer.testing.CliRunner mangles the output streams with click 8.4, so the
# commands are invoked through click's runner instead.
from click.testing import CliRunner
from dishka import Container, make_container
from slidetap_example import (
    ExampleImagePreProcessor,
    ExampleMapperInjector,
    ExampleMetadataExportInterface,
    ExampleMetadataImportInterface,
    ExampleSchema,
)
from slidetap_example.schema import ExampleSchemaInterface
from sqlalchemy import create_engine
from typer.main import get_command

from slidetap import BaseProvider
from slidetap.config import DatabaseConfig
from slidetap.database import Base
from slidetap.mappers_cli import app
from slidetap.service_provider import ConfigProvider
from slidetap.services import DatabaseService


def create_container() -> Container:
    """Create a container of the example application, reading the database
    from SLIDETAP_DBURI as an application does."""
    base_provider = BaseProvider(
        schema_interface=ExampleSchemaInterface,
        metadata_export_interface=ExampleMetadataExportInterface,
        metadata_import_interface=ExampleMetadataImportInterface,
        mapper_injector=ExampleMapperInjector,
    )
    base_provider.provide(ExampleImagePreProcessor)
    config_provider = ConfigProvider(
        database_config=lambda: DatabaseConfig(os.environ["SLIDETAP_DBURI"], False)
    )
    return make_container(base_provider, config_provider)


@pytest.fixture
def uri(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    uri = f"sqlite:///{tmp_path.joinpath('test.db')}"
    Base.metadata.create_all(bind=create_engine(uri))
    # Set by the command from --db-uri, and so put back after the test.
    monkeypatch.setenv("SLIDETAP_DBURI", "")
    return uri


@pytest.fixture
def database_service(uri: str) -> DatabaseService:
    return DatabaseService(DatabaseConfig(uri, False))


def test_set_up_gives_families_and_injects_mappers(
    uri: str, database_service: DatabaseService
):
    """The `slidetap-mappers set-up` command, from parsing to stored mappers."""
    # Arrange
    attribute = ExampleSchema().specimen.attributes["collection"].uid
    with database_service.get_session() as session:
        stored_uid = database_service.add_mapper(
            session, "stored", attribute, attribute
        ).uid

    # Act
    result = CliRunner().invoke(
        get_command(app),
        [
            "set-up",
            "--container",
            f"{__name__}:create_container",
            "--db-uri",
            uri,
        ],
    )

    # Assert
    assert result.exit_code == 0, result.output
    with database_service.get_session() as session:
        stored = database_service.get_mapper(session, stored_uid)
        assert stored.family_uid == ExampleSchema().family_uid
        assert list(database_service.get_mapper_groups(session)) != []


@pytest.mark.parametrize(
    "container",
    ["no_colon", f"{__name__}:missing", f"{__name__}:", ":create_container"],
)
def test_set_up_refuses_what_is_not_a_container_factory(container: str, uri: str):
    # Act
    result = CliRunner().invoke(
        get_command(app), ["set-up", "--container", container, "--db-uri", uri]
    )

    # Assert
    assert result.exit_code != 0
