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

"""What the delete, export and search tasks leave behind when they fail or are
run again, and what the scheduler does when a task cannot be deferred."""

import datetime
from collections.abc import Callable
from uuid import UUID

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from slidetap_example import ExampleSchema

from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseProject,
)
from slidetap.external_interfaces import (
    MetadataExportInterface,
    TransientTaskError,
)
from slidetap.model import (
    BatchStatus,
    ProjectStatus,
)
from slidetap.services import (
    BatchService,
    DatabaseService,
    ProjectService,
    SchemaService,
    StorageService,
)
from slidetap.task.tasks import (
    delete_batch,
    delete_project,
    process_metadata_export,
)


def _retried(exception: BaseException) -> bool:
    return True


def _not_retried(exception: BaseException) -> bool:
    return False


class StoredBatch:
    def __init__(self, project_uid: UUID, batch_uid: UUID, dataset_uid: UUID):
        self.project_uid = project_uid
        self.batch_uid = batch_uid
        self.dataset_uid = dataset_uid


def _add_batch(
    database_service: DatabaseService,
    schema: ExampleSchema,
    status: BatchStatus,
    project_status: ProjectStatus = ProjectStatus.IN_PROGRESS,
) -> StoredBatch:
    with database_service.get_session() as session:
        dataset = DatabaseDataset("dataset", schema.dataset.uid)
        session.add(dataset)
        project = DatabaseProject(
            "project",
            schema.uid,
            schema.project.uid,
            dataset.uid,
            datetime.datetime(2026, 10, 16),
        )
        project.status = project_status
        session.add(project)
        batch = DatabaseBatch("batch", project.uid, datetime.datetime(2026, 10, 16))
        batch.status = status
        session.add(batch)
        session.commit()
        return StoredBatch(project.uid, batch.uid, dataset.uid)


@pytest.fixture()
def schema_service(decoy: Decoy) -> SchemaService:
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.change_refusal(Anything())).then_return(None)
    return schema_service


@pytest.mark.integration
class TestDeleteTasks:
    def test_a_batch_delete_failing_transiently_on_the_last_attempt_is_failed(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
    ):
        """Failed rather than left deleting, so that marking it as deleting
        again reruns the delete."""
        # Arrange
        stored = _add_batch(sqlite_database_service, schema, BatchStatus.DELETING)
        batch_service = decoy.mock(cls=BatchService)
        decoy.when(batch_service.delete(stored.batch_uid)).then_raise(
            TransientTaskError("Database unreachable")
        )

        # Act
        delete_batch.func.__wrapped__(  # type: ignore[attr-defined]
            batch_uid=stored.batch_uid,
            batch_service=batch_service,
            database_service=sqlite_database_service,
            storage_service=decoy.mock(cls=StorageService),
            will_retry=_not_retried,
        )

        # Assert
        decoy.verify(
            batch_service.set_as_failed(
                stored.batch_uid, message="Delete failed: Database unreachable"
            ),
            times=1,
        )

    def test_a_batch_delete_failing_transiently_before_the_last_attempt_raises(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(sqlite_database_service, schema, BatchStatus.DELETING)
        batch_service = decoy.mock(cls=BatchService)
        decoy.when(batch_service.delete(stored.batch_uid)).then_raise(
            TransientTaskError("Database unreachable")
        )

        # Act & Assert
        with pytest.raises(TransientTaskError):
            delete_batch.func.__wrapped__(  # type: ignore[attr-defined]
                batch_uid=stored.batch_uid,
                batch_service=batch_service,
                database_service=sqlite_database_service,
                storage_service=decoy.mock(cls=StorageService),
                will_retry=_retried,
            )
        decoy.verify(
            batch_service.set_as_failed(Anything(), message=Anything()), times=0
        )

    def test_a_project_delete_failing_transiently_on_the_last_attempt_is_failed(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service,
            schema,
            BatchStatus.INITIALIZED,
            project_status=ProjectStatus.DELETING,
        )
        project_service = decoy.mock(cls=ProjectService)
        decoy.when(project_service.delete(stored.project_uid)).then_raise(
            TransientTaskError("Database unreachable")
        )

        # Act
        delete_project.func.__wrapped__(  # type: ignore[attr-defined]
            project_uid=stored.project_uid,
            project_service=project_service,
            database_service=sqlite_database_service,
            will_retry=_not_retried,
        )

        # Assert
        decoy.verify(
            project_service.set_as_failed(
                stored.project_uid, message="Delete failed: Database unreachable"
            ),
            times=1,
        )


@pytest.mark.integration
class TestProcessMetadataExport:
    @pytest.mark.parametrize(
        ["will_retry", "reverted"], [(_not_retried, 1), (_retried, 0)]
    )
    def test_a_transient_failure_is_reverted_only_on_the_last_attempt(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        will_retry: Callable[[BaseException], bool],
        reverted: int,
    ):
        """Reverted rather than left exporting, so that it can be exported
        again."""
        # Arrange
        stored = _add_batch(
            sqlite_database_service,
            schema,
            BatchStatus.LOCKED,
            project_status=ProjectStatus.EXPORTING,
        )
        metadata_export_interface = decoy.mock(cls=MetadataExportInterface)
        decoy.when(metadata_export_interface.export(Anything(), Anything())).then_raise(
            TransientTaskError("Outbox unreachable")
        )
        project_service = decoy.mock(cls=ProjectService)

        # Act
        try:
            process_metadata_export.func.__wrapped__(  # type: ignore[attr-defined]
                project_id=stored.project_uid,
                metadata_export_interface=metadata_export_interface,
                project_service=project_service,
                database_service=sqlite_database_service,
                schema_service=schema_service,
                will_retry=will_retry,
            )
        except TransientTaskError:
            assert reverted == 0

        # Assert
        decoy.verify(
            project_service.revert_export(Anything(), Anything()), times=reverted
        )
