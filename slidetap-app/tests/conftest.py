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
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from slidetap_example import ExampleSchema
from sqlalchemy import create_engine

from slidetap.config import DatabaseConfig
from slidetap.database import Base
from slidetap.external_interfaces import (
    SchemaInterface,
    SchemaMigration,
)
from slidetap.external_interfaces.implementations.migration import EntityMigrator
from slidetap.model import (
    Batch,
    BatchStatus,
    Code,
    CodeAttribute,
    Dataset,
    EntityMigrationResult,
    Item,
    Project,
    RootSchema,
)
from slidetap.services import DatabaseService, SchemaService

T = TypeVar("T", bound=Project | Dataset | Item)


class MovingMigrator(EntityMigrator[T]):
    """Moves every attribute as it is to the target attribute of its tag."""

    def migrate(self, entity: T) -> EntityMigrationResult:
        """Move every attribute of an entity to the target schema."""
        return EntityMigrationResult(
            schema_uid=self.target.uid,
            attributes=self._move_all_except(entity.attributes),
            private_attributes=self._move_all_except(
                entity.private_attributes, private=True
            ),
        )


@pytest.fixture
def schema():
    yield ExampleSchema()


@pytest.fixture
def schema_service_of(
    decoy: Decoy, sqlite_database_service: DatabaseService
) -> Callable[..., SchemaService]:
    """Builds a schema service as the plugin's interfaces provide it: of the
    root of new projects, the previous roots, and the migrations."""

    def schema_service_of(
        root: RootSchema,
        *previous_roots: RootSchema,
        migrations: Mapping[UUID, SchemaMigration] | None = None,
    ) -> SchemaService:
        schema_interface = decoy.mock(cls=SchemaInterface)
        decoy.when(schema_interface.root()).then_return(root)
        decoy.when(schema_interface.previous_roots()).then_return(previous_roots)
        for previous_root in previous_roots:
            migration = (migrations or {}).get(previous_root.uid)
            if migration is not None:
                decoy.when(schema_interface.migration_from(previous_root)).then_return(
                    migration
                )
        return SchemaService(schema_interface, sqlite_database_service)

    return schema_service_of


OTHER_ROOT_SCHEMA_UID = UUID("0d5b3c1e-9a0f-4f5e-8f55-2f7b5f0a6c11")
OTHER_SEX_SCHEMA_UID = UUID("5a0e2b67-3c1d-4e8a-9f0b-7d6c5e4f3a21")


@pytest.fixture
def other_schema(schema: ExampleSchema) -> RootSchema:
    """The example schema as a second root, a new version of it in its family.

    The same item schemas and relations under the same uids, with the sex of
    the patient changed: another uid and other allowed values. Every other
    attribute is shared with the example schema.
    """
    patient = schema.patient
    sex = patient.attributes["sex"].model_copy(
        update={"uid": OTHER_SEX_SCHEMA_UID, "allowed_values": ("Male", "Female")}
    )
    return RootSchema(
        uid=OTHER_ROOT_SCHEMA_UID,
        name=schema.name,
        version="2",
        family_uid=schema.family_uid,
        project=schema.project,
        dataset=schema.dataset,
        images=dict(schema.images),
        samples={
            **schema.samples,
            patient.uid: patient.model_copy(update={"attributes": {"sex": sex}}),
        },
        observations=dict(schema.observations),
    )


@pytest.fixture()
def sqlite_database_service(tmp_path: Path) -> DatabaseService:
    """A DatabaseService backed by a throwaway SQLite file.

    Named apart from the `database_service` fixtures in the service tests,
    which are Decoy mocks: a test that asks for this one gets a real database.
    """
    uri = f"sqlite:///{tmp_path / 'test.db'}"
    Base.metadata.create_all(bind=create_engine(uri))
    return DatabaseService(DatabaseConfig(uri, False))


@pytest.fixture()
def mapper_uid(sqlite_database_service: DatabaseService) -> UUID:
    with sqlite_database_service.get_session() as session:
        mapper = sqlite_database_service.add_mapper(
            session, "test-mapper", uuid4(), uuid4()
        )
        return mapper.uid


@pytest.fixture()
def code_attribute() -> CodeAttribute:
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=uuid4(),
        original_value=Code(code="code", scheme="scheme", meaning="meaning"),
    )


@pytest.fixture()
def dataset(schema: RootSchema):
    yield Dataset(
        uid=uuid4(),
        name="dataset name",
        schema_uid=schema.dataset.uid,
    )


@pytest.fixture()
def project(schema: RootSchema, dataset: Dataset):
    project = Project(
        uid=uuid4(),
        name="project name",
        root_schema_uid=schema.uid,
        schema_uid=schema.project.uid,
        dataset_uid=dataset.uid,
        created=datetime.datetime(2021, 1, 1),
        attributes={},
        mapper_groups=[],
    )
    yield project


@pytest.fixture()
def batch(project: Project):
    return Batch(
        uid=uuid4(),
        name="batch name",
        status=BatchStatus.INITIALIZED,
        project_uid=project.uid,
        is_default=True,
        created=datetime.datetime(2021, 1, 1),
    )
