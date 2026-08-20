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
from slidetap_example import ExampleSchema
from sqlalchemy import create_engine

from slidetap.config import DatabaseConfig
from slidetap.database import Base
from slidetap.model import (
    Batch,
    BatchStatus,
    Code,
    CodeAttribute,
    Dataset,
    Project,
    RootSchema,
)
from slidetap.services import DatabaseService


@pytest.fixture
def schema():
    yield ExampleSchema()


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
