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
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from slidetap_example import ExampleSchema
from sqlalchemy import select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseMetadataSearchItem,
    DatabaseProject,
    DatabaseSample,
)
from slidetap.external_interfaces import (
    MetadataExportInterface,
    MetadataImportInterface,
    TransientTaskError,
)
from slidetap.model import (
    BatchStatus,
    MetadataImportStatus,
    MetadataSearchResult,
    ProjectStatus,
)
from slidetap.services import (
    BatchService,
    DatabaseService,
    ItemService,
    MetadataSearchItemService,
    ProjectService,
    ReviewService,
    SchemaService,
    StorageService,
    ValidationService,
)
from slidetap.task import DeferError, Scheduler
from slidetap.task import scheduler as scheduler_module
from slidetap.task.tasks import (
    delete_batch,
    delete_project,
    process_metadata_export,
    process_metadata_import,
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
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
    ):
        """Failed rather than left deleting, so that marking it as deleting
        again reruns the delete."""
        # Arrange
        stored = _add_batch(stored_database_service, schema, BatchStatus.DELETING)
        batch_service = decoy.mock(cls=BatchService)
        decoy.when(batch_service.delete(stored.batch_uid)).then_raise(
            TransientTaskError("Database unreachable")
        )

        # Act
        delete_batch.func.__wrapped__(  # type: ignore[attr-defined]
            batch_uid=stored.batch_uid,
            batch_service=batch_service,
            database_service=stored_database_service,
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
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(stored_database_service, schema, BatchStatus.DELETING)
        batch_service = decoy.mock(cls=BatchService)
        decoy.when(batch_service.delete(stored.batch_uid)).then_raise(
            TransientTaskError("Database unreachable")
        )

        # Act & Assert
        with pytest.raises(TransientTaskError):
            delete_batch.func.__wrapped__(  # type: ignore[attr-defined]
                batch_uid=stored.batch_uid,
                batch_service=batch_service,
                database_service=stored_database_service,
                storage_service=decoy.mock(cls=StorageService),
                will_retry=_retried,
            )
        decoy.verify(
            batch_service.set_as_failed(Anything(), message=Anything()), times=0
        )

    def test_a_project_delete_failing_transiently_on_the_last_attempt_is_failed(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            stored_database_service,
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
            database_service=stored_database_service,
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
        stored_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        will_retry: Callable[[BaseException], bool],
        reverted: int,
    ):
        """Reverted rather than left exporting, so that it can be exported
        again."""
        # Arrange
        stored = _add_batch(
            stored_database_service,
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
                database_service=stored_database_service,
                schema_service=schema_service,
                will_retry=will_retry,
            )
        except TransientTaskError:
            assert reverted == 0

        # Assert
        decoy.verify(
            project_service.revert_export(Anything(), Anything()), times=reverted
        )


@pytest.mark.integration
class TestProcessMetadataImportRunAgain:
    def test_a_search_run_again_does_not_duplicate_search_items(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
    ):
        """The failure this guards against: the retry of a search that failed
        part-way records every result the first attempt recorded a second
        time, and imports what it imported again."""
        # Arrange
        stored = _add_batch(
            stored_database_service, schema, BatchStatus.METADATA_SEARCHING
        )
        schema_uid = schema.patient_schema_uid
        imported = MetadataSearchResult.succeeded("patient-1", schema_uid, items=[])
        failed = MetadataSearchResult.failed("patient-2", schema_uid, "Not found")
        added = MetadataSearchResult.succeeded("patient-3", schema_uid, items=[])

        def first_attempt() -> Iterator[MetadataSearchResult]:
            yield imported
            yield failed
            raise TransientTaskError("Source unreachable")

        def second_attempt() -> Iterator[MetadataSearchResult]:
            yield imported
            yield failed
            yield added

        attempts = iter([first_attempt(), second_attempt()])
        metadata_import_interface = decoy.mock(cls=MetadataImportInterface)
        decoy.when(
            metadata_import_interface.search(Anything(), Anything(), Anything())
        ).then_do(lambda batch, dataset, parameters: next(attempts))
        item_service = decoy.mock(cls=ItemService)
        added_identifiers: list[str] = []

        def _add(result: MetadataSearchResult, session: Session) -> UUID:
            """Store the patient the result is for, as importing it would."""
            added_identifiers.append(result.identifier)
            patient = DatabaseSample(
                stored.dataset_uid, stored.batch_uid, schema_uid, result.identifier
            )
            session.add(patient)
            session.flush()
            return patient.uid

        decoy.when(
            item_service.add_search_result(Anything(), Anything(), session=Anything())
        ).then_do(lambda result, mappers, session: _add(result, session))
        batch_service = BatchService(
            schema_service=decoy.mock(cls=SchemaService),
            validation_service=decoy.mock(cls=ValidationService),
            database_service=stored_database_service,
            review_service=decoy.mock(cls=ReviewService),
        )

        def run(will_retry: Callable[[BaseException], bool]) -> None:
            process_metadata_import.func.__wrapped__(  # type: ignore[attr-defined]
                batch_uid=stored.batch_uid,
                search_parameters={},
                metadata_import_interface=metadata_import_interface,
                database_service=stored_database_service,
                batch_service=batch_service,
                item_service=item_service,
                search_item_service=MetadataSearchItemService(stored_database_service),
                schema_service=schema_service,
                will_retry=will_retry,
            )

        # Act
        with pytest.raises(TransientTaskError):
            run(_retried)
        run(_not_retried)

        # Assert
        with stored_database_service.get_session() as session:
            search_items = session.scalars(select(DatabaseMetadataSearchItem)).all()
            statuses = {item.identifier: item.status for item in search_items}
        assert len(search_items) == 3
        assert statuses == {
            "patient-1": MetadataImportStatus.COMPLETE,
            "patient-2": MetadataImportStatus.FAILED,
            "patient-3": MetadataImportStatus.COMPLETE,
        }
        assert added_identifiers == ["patient-1", "patient-3"]
        with stored_database_service.get_session() as session:
            batch = stored_database_service.get_batch(session, stored.batch_uid)
            assert batch.status == BatchStatus.METADATA_SEARCH_COMPLETE


class FakeTask:
    """A task whose deferring fails for the image uids it is given."""

    name = "fake_task"

    def __init__(self, failing: set[str]):
        self._failing = failing
        self.deferred: list[str] = []

    def configure(self, **options: Any) -> "FakeTask":
        return self

    def defer(self, image_uid: str) -> None:
        self.deferred.append(image_uid)
        if image_uid in self._failing:
            raise ConnectionError("Queue unreachable")


@pytest.mark.unittest
class TestSchedulerDeferral:
    def test_a_failure_to_defer_does_not_skip_the_other_images(
        self, decoy: Decoy, monkeypatch: pytest.MonkeyPatch
    ):
        # Arrange
        image_uids = [uuid4(), uuid4(), uuid4()]
        task = FakeTask({str(image_uids[1])})
        monkeypatch.setattr(scheduler_module, "download_and_pre_process_image", task)
        scheduler = Scheduler(decoy.mock(cls=scheduler_module.TaskApp))

        # Act
        with pytest.raises(DeferError) as raised:
            scheduler.pre_process_images(image_uids)

        # Assert
        assert task.deferred == [str(image_uid) for image_uid in image_uids]
        assert list(raised.value.failures) == [image_uids[1]]

    def test_a_failure_to_defer_one_image_raises(
        self, decoy: Decoy, monkeypatch: pytest.MonkeyPatch
    ):
        # Arrange
        image_uid = uuid4()
        task = FakeTask({str(image_uid)})
        monkeypatch.setattr(scheduler_module, "post_process_image", task)
        scheduler = Scheduler(decoy.mock(cls=scheduler_module.TaskApp))
        image = type("ImageStub", (), {"uid": image_uid})()

        # Act & Assert
        with pytest.raises(ConnectionError):
            scheduler.post_process_image(image)  # type: ignore[arg-type]
