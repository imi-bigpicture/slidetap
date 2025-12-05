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

import io
from uuid import uuid4

import pytest
from decoy import Decoy
from slidetap.database import DatabaseBatch
from slidetap.external_interfaces import MetadataImportInterface
from slidetap.model import (
    Batch,
    Dataset,
    File,
    ItemSchema,
    Project,
)
from slidetap.services import (
    BatchService,
    DatabaseService,
    SchemaService,
)
from slidetap.task.scheduler import Scheduler
from slidetap.web.services.metadata_import_service import MetadataImportService
from sqlalchemy.orm import Session


@pytest.fixture()
def batch_service(decoy: Decoy) -> BatchService:
    return decoy.mock(cls=BatchService)


@pytest.fixture()
def database_service(decoy: Decoy) -> DatabaseService:
    return decoy.mock(cls=DatabaseService)


@pytest.fixture()
def metadata_import_interface(decoy: Decoy):
    return decoy.mock(cls=MetadataImportInterface[str])


@pytest.fixture()
def schema_service(decoy: Decoy):
    return decoy.mock(cls=SchemaService)


@pytest.fixture()
def scheduler(decoy: Decoy):
    return decoy.mock(cls=Scheduler)


@pytest.fixture()
def metadata_import_service(
    scheduler: Scheduler,
    batch_service: BatchService,
    database_service: DatabaseService,
    schema_service: SchemaService,
    metadata_import_interface: MetadataImportInterface,
):
    return MetadataImportService(
        scheduler,
        batch_service,
        database_service,
        schema_service,
        metadata_import_interface,
    )


@pytest.mark.unittest
class TestMetadataImportServiceService:
    def test_search(
        self,
        decoy: Decoy,
        batch: Batch,
        database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        metadata_import_interface: MetadataImportInterface[str],
        metadata_import_service: MetadataImportService,
        scheduler: Scheduler,
    ):
        # Arrange
        file = File(
            filename="test.json",
            content_type="application/json",
            stream=io.BytesIO(b"file content"),
        )
        search_parameters = "search_parameters"
        item_schema = decoy.mock(cls=ItemSchema)
        session = decoy.mock(cls=Session)
        database_batch = decoy.mock(cls=DatabaseBatch)

        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(database_service.get_batch(session, batch.uid)).then_return(
            database_batch
        )
        decoy.when(schema_service.items).then_return({item_schema.uid: item_schema})
        decoy.when(batch_service.set_as_searching(database_batch, session)).then_return(
            batch
        )
        decoy.when(metadata_import_interface.parse_file(file)).then_return(
            search_parameters
        )

        # Act
        result = metadata_import_service.search(batch.uid, file)

        # Assert
        assert result == batch
        decoy.verify(batch_service.reset(database_batch, session), times=1)
        decoy.verify(
            database_service.delete_items(session, item_schema, batch.uid), times=1
        )
        decoy.verify(
            scheduler.metadata_batch_import(batch, search_parameters=search_parameters),
            times=1,
        )

    def test_create_project(
        self,
        decoy: Decoy,
        metadata_import_interface: MetadataImportInterface,
        metadata_import_service: MetadataImportService,
    ):
        # Arrange
        name = "Test Project"
        dataset_uid = uuid4()
        project = decoy.mock(cls=Project)

        decoy.when(
            metadata_import_interface.create_project(name, dataset_uid)
        ).then_return(project)

        # Act
        result = metadata_import_service.create_project(name, dataset_uid)

        # Assert
        assert result == project

    def test_create_dataset(
        self,
        decoy: Decoy,
        metadata_import_interface: MetadataImportInterface,
        metadata_import_service: MetadataImportService,
    ):
        # Arrange
        name = "Test Dataset"
        dataset = decoy.mock(cls=Dataset)

        decoy.when(metadata_import_interface.create_dataset(name)).then_return(dataset)

        # Act
        result = metadata_import_service.create_dataset(name)

        # Assert
        assert result == dataset
