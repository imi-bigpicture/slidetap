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
from sqlalchemy.orm import Session

from slidetap.database import DatabaseBatch, NotAllowedActionError
from slidetap.external_interfaces import FileParseError, MetadataImportInterface
from slidetap.model import (
    Batch,
    BatchStatus,
    Dataset,
    File,
    ItemSchema,
    Project,
)
from slidetap.services import (
    BatchService,
    DatabaseService,
    MetadataSearchItemService,
    SchemaService,
)
from slidetap.task.scheduler import Scheduler
from slidetap.web.services.metadata_import_service import MetadataImportService


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
def search_item_service(decoy: Decoy):
    return decoy.mock(cls=MetadataSearchItemService)


@pytest.fixture()
def metadata_import_service(
    scheduler: Scheduler,
    batch_service: BatchService,
    database_service: DatabaseService,
    schema_service: SchemaService,
    search_item_service: MetadataSearchItemService,
    metadata_import_interface: MetadataImportInterface,
):
    return MetadataImportService(
        scheduler,
        batch_service,
        database_service,
        schema_service,
        search_item_service,
        metadata_import_interface,
    )


@pytest.mark.unittest
class TestMetadataImportServiceService:
    @pytest.mark.asyncio
    async def test_search(
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
        result = await metadata_import_service.search(batch.uid, file)

        # Assert
        assert result == batch
        decoy.verify(batch_service.reset(database_batch, session), times=1)
        decoy.verify(
            batch_service.move_shared_items_to_other_batch(database_batch, session),
            times=1,
        )
        decoy.verify(
            database_service.delete_items(session, item_schema, batch.uid), times=1
        )
        decoy.verify(
            await scheduler.metadata_batch_import(
                batch, search_parameters=search_parameters
            ),
            times=1,
        )

    @pytest.mark.asyncio
    async def test_a_batch_that_cannot_be_searched_is_not_handed_the_document(
        self,
        decoy: Decoy,
        batch: Batch,
        database_service: DatabaseService,
        batch_service: BatchService,
        metadata_import_interface: MetadataImportInterface[str],
        metadata_import_service: MetadataImportService,
    ):
        """Whatever is wrong with the document is not what is wrong here."""
        # Arrange
        file = File(
            filename="test.json",
            content_type="application/json",
            stream=io.BytesIO(b"file content"),
        )
        session = decoy.mock(cls=Session)
        database_batch = decoy.mock(cls=DatabaseBatch)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(database_service.get_batch(session, batch.uid)).then_return(
            database_batch
        )
        decoy.when(batch_service.assert_can_search(database_batch)).then_raise(
            NotAllowedActionError("Can only search non-started batches")
        )

        # Act
        with pytest.raises(NotAllowedActionError):
            await metadata_import_service.search(batch.uid, file)

        # Assert
        decoy.verify(metadata_import_interface.parse_file(file), times=0)

    @pytest.mark.asyncio
    async def test_a_document_that_cannot_be_read_leaves_the_batch_alone(
        self,
        decoy: Decoy,
        batch: Batch,
        database_service: DatabaseService,
        batch_service: BatchService,
        metadata_import_interface: MetadataImportInterface[str],
        metadata_import_service: MetadataImportService,
    ):
        """Emptied and set as searching first, the batch would be left
        searching for something nothing is going to search for."""
        # Arrange
        file = File(
            filename="test.json",
            content_type="application/json",
            stream=io.BytesIO(b"file content"),
        )
        session = decoy.mock(cls=Session)
        database_batch = decoy.mock(cls=DatabaseBatch)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(database_service.get_batch(session, batch.uid)).then_return(
            database_batch
        )
        decoy.when(metadata_import_interface.parse_file(file)).then_raise(
            ValueError("Row 3 gives no Case ID.")
        )

        # Act
        with pytest.raises(FileParseError) as raised:
            await metadata_import_service.search(batch.uid, file)

        # Assert
        assert "Row 3" in str(raised.value)
        decoy.verify(batch_service.reset(database_batch, session), times=0)
        decoy.verify(batch_service.set_as_searching(database_batch, session), times=0)

    @pytest.mark.asyncio
    async def test_search_failed_enqueue_sets_batch_as_failed(
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
        session = decoy.mock(cls=Session)
        database_batch = decoy.mock(cls=DatabaseBatch)
        failed_batch = batch.model_copy(
            update={
                "status": BatchStatus.FAILED,
                "status_message": "Failed to start metadata search: no worker",
            }
        )

        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(database_service.get_batch(session, batch.uid)).then_return(
            database_batch
        )
        decoy.when(schema_service.items).then_return({})
        decoy.when(batch_service.set_as_searching(database_batch, session)).then_return(
            batch
        )
        decoy.when(metadata_import_interface.parse_file(file)).then_return(
            search_parameters
        )
        decoy.when(
            await scheduler.metadata_batch_import(
                batch, search_parameters=search_parameters
            )
        ).then_raise(RuntimeError("no worker"))
        decoy.when(
            batch_service.set_as_failed(
                batch.uid, message="Failed to start metadata search: no worker"
            )
        ).then_return(failed_batch)

        # Act
        result = await metadata_import_service.search(batch.uid, file)

        # Assert
        assert result.status == BatchStatus.FAILED
        assert result.status_message == "Failed to start metadata search: no worker"

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
