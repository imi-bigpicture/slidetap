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
from uuid import uuid4

import pytest
from slidetap.model import (
    Batch,
    BatchStatus,
    Dataset,
    Project,
    RootSchema,
)
from slidetap_example import ExampleSchema


@pytest.fixture
def schema():
    yield ExampleSchema()


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
