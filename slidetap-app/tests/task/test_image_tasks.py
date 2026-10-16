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

"""What the image tasks leave behind when they fail, and what they hold while
they work.

Run against the database rather than mocks, since what is pinned is the status
an image and its batch are left in: a transient failure on the last attempt
has to leave the image failed and the batch settled, rather than waiting for a
retry that is not coming.
"""

import datetime
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from procrastinate.jobs import Job
from slidetap_example import ExampleSchema
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
    DatabaseProject,
)
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataImportInterface,
    TransientTaskError,
)
from slidetap.image_processor.dicom_metadata import DicomMetadataWriter
from slidetap.model import BatchStatus, Image, ImageFile, ImageFormat, ImageStatus
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    ItemService,
    MetadataSearchItemService,
    ReviewService,
    SchemaService,
    StorageService,
    ValidationService,
)
from slidetap.task.dishka_integration import retry_check
from slidetap.task.tasks import (
    _TRANSIENT_RETRY,
    _reset_state_for_stalled_job,
    download_and_pre_process_image,
    post_process_image,
    process_metadata_import,
    retry_stalled_jobs,
    store_batch_images_to_outbox,
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
    database_service: DatabaseService, schema: ExampleSchema, status: BatchStatus
) -> StoredBatch:
    with database_service.get_session() as session:
        dataset = DatabaseDataset("dataset", schema.dataset.uid)
        session.add(dataset)
        project = DatabaseProject(
            "project",
            schema.uid,
            schema.project.uid,
            dataset.uid,
            datetime.datetime(2026, 10, 15),
        )
        session.add(project)
        batch = DatabaseBatch("batch", project.uid, datetime.datetime(2026, 10, 15))
        batch.status = status
        session.add(batch)
        session.commit()
        return StoredBatch(project.uid, batch.uid, dataset.uid)


def _add_image(
    database_service: DatabaseService,
    schema: ExampleSchema,
    stored: StoredBatch,
    status: ImageStatus,
    identifier: str = "PL1234-20-1",
    folder_path: str | None = None,
) -> UUID:
    with database_service.get_session() as session:
        image = DatabaseImage(
            dataset_uid=stored.dataset_uid,
            batch_uid=stored.batch_uid,
            schema_uid=schema.image.uid,
            identifier=identifier,
            format=ImageFormat.OTHER_WSI,
        )
        image.status = status
        image.selected = True
        image.folder_path = folder_path
        session.add(image)
        session.commit()
        return image.uid


def _image_status(database_service: DatabaseService, image_uid: UUID) -> ImageStatus:
    with database_service.get_session() as session:
        return database_service.get_image(session, image_uid).status


def _batch_status(database_service: DatabaseService, batch_uid: UUID) -> BatchStatus:
    with database_service.get_session() as session:
        return database_service.get_batch(session, batch_uid).status


@pytest.fixture()
def open_sessions(
    monkeypatch: pytest.MonkeyPatch, sqlite_database_service: DatabaseService
) -> list[Session]:
    """The sessions the database service has open, as the tasks run."""
    opened: list[Session] = []
    get_session = sqlite_database_service.get_session

    @contextmanager
    def tracking_get_session(
        session: Session | None = None, commit: bool | None = None
    ) -> Iterator[Session]:
        with get_session(session, commit) as tracked:
            opened.append(tracked)
            try:
                yield tracked
            finally:
                opened.remove(tracked)

    monkeypatch.setattr(sqlite_database_service, "get_session", tracking_get_session)
    return opened


@pytest.fixture()
def schema_service(decoy: Decoy, schema: ExampleSchema) -> SchemaService:
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.change_refusal(Anything())).then_return(None)
    decoy.when(schema_service.root_of(Anything())).then_return(schema)
    return schema_service


@pytest.fixture()
def batch_service(
    decoy: Decoy, sqlite_database_service: DatabaseService
) -> BatchService:
    return BatchService(
        schema_service=decoy.mock(cls=SchemaService),
        validation_service=decoy.mock(cls=ValidationService),
        database_service=sqlite_database_service,
        review_service=decoy.mock(cls=ReviewService),
    )


@pytest.fixture()
def storage_service(decoy: Decoy) -> StorageService:
    return decoy.mock(cls=StorageService)


def _download_and_pre_process(
    image_uid: UUID,
    database_service: DatabaseService,
    batch_service: BatchService,
    schema_service: SchemaService,
    image_import_interface: ImageImportInterface,
    metadata_import_interface: MetadataImportInterface,
    will_retry: Callable[[BaseException], bool],
    review_service: ReviewService,
) -> None:
    download_and_pre_process_image.func.__wrapped__(  # type: ignore[attr-defined]
        image_uid=image_uid,
        task_id="1",
        image_import_interface=image_import_interface,
        metadata_import_interface=metadata_import_interface,
        database_service=database_service,
        review_service=review_service,
        batch_service=batch_service,
        attribute_service=AttributeService.__new__(AttributeService),
        schema_service=schema_service,
        will_retry=will_retry,
    )


def _post_process(
    image_uid: UUID,
    database_service: DatabaseService,
    batch_service: BatchService,
    schema_service: SchemaService,
    storage_service: StorageService,
    image_export_interface: ImageExportInterface,
    will_retry: Callable[[BaseException], bool],
) -> None:
    post_process_image.func.__wrapped__(  # type: ignore[attr-defined]
        image_uid=image_uid,
        task_id="1",
        image_export_interface=image_export_interface,
        database_service=database_service,
        batch_service=batch_service,
        storage_service=storage_service,
        schema_service=schema_service,
        will_retry=will_retry,
    )


@pytest.mark.integration
class TestDownloadAndPreProcessImage:
    def test_a_transient_failure_on_the_last_attempt_settles_the_batch(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        schema: ExampleSchema,
    ):
        """The failure this guards against: the image set back as not started
        for a retry that never comes, holding the batch at pre-processing."""
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.IMAGE_PRE_PROCESSING
        )
        image_uid = _add_image(
            sqlite_database_service, schema, stored, ImageStatus.NOT_STARTED
        )
        image_import_interface = decoy.mock(cls=ImageImportInterface)
        decoy.when(image_import_interface.download(Anything(), Anything())).then_raise(
            TransientTaskError("Source unreachable")
        )
        review_service = decoy.mock(cls=ReviewService)

        # Act
        _download_and_pre_process(
            image_uid,
            sqlite_database_service,
            batch_service,
            schema_service,
            image_import_interface,
            decoy.mock(cls=MetadataImportInterface),
            _not_retried,
            review_service,
        )

        # Assert
        assert (
            _image_status(sqlite_database_service, image_uid)
            == ImageStatus.DOWNLOADING_FAILED
        )
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )
        decoy.verify(
            review_service.item_became_invalid(image_uid, session=Anything()),
            times=1,
        )

    def test_a_transient_failure_that_is_retried_sets_the_image_back(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.IMAGE_PRE_PROCESSING
        )
        image_uid = _add_image(
            sqlite_database_service, schema, stored, ImageStatus.NOT_STARTED
        )
        image_import_interface = decoy.mock(cls=ImageImportInterface)
        decoy.when(image_import_interface.download(Anything(), Anything())).then_raise(
            TransientTaskError("Source unreachable")
        )

        # Act & Assert
        with pytest.raises(TransientTaskError):
            _download_and_pre_process(
                image_uid,
                sqlite_database_service,
                batch_service,
                schema_service,
                image_import_interface,
                decoy.mock(cls=MetadataImportInterface),
                _retried,
                decoy.mock(cls=ReviewService),
            )
        assert (
            _image_status(sqlite_database_service, image_uid) == ImageStatus.NOT_STARTED
        )
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_PRE_PROCESSING
        )

    def test_no_session_is_open_while_downloading_or_reading(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        open_sessions: list[Session],
        batch_service: BatchService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.IMAGE_PRE_PROCESSING
        )
        image_uid = _add_image(
            sqlite_database_service, schema, stored, ImageStatus.NOT_STARTED
        )
        sessions_while_working: list[int] = []

        def download(image: Image, project: Any) -> tuple[Path, list[Path]]:
            sessions_while_working.append(len(open_sessions))
            return tmp_path, []

        def import_image_metadata(
            image: Image, batch: Any, project: Any, task_id: str
        ) -> Image:
            sessions_while_working.append(len(open_sessions))
            raise ValueError("Unreadable file")

        image_import_interface = decoy.mock(cls=ImageImportInterface)
        decoy.when(image_import_interface.download(Anything(), Anything())).then_do(
            download
        )
        metadata_import_interface = decoy.mock(cls=MetadataImportInterface)
        decoy.when(
            metadata_import_interface.import_image_metadata(
                Anything(), Anything(), Anything(), Anything()
            )
        ).then_do(import_image_metadata)

        # Act
        _download_and_pre_process(
            image_uid,
            sqlite_database_service,
            batch_service,
            schema_service,
            image_import_interface,
            metadata_import_interface,
            _not_retried,
            decoy.mock(cls=ReviewService),
        )

        # Assert
        assert sessions_while_working == [0, 0]
        assert (
            _image_status(sqlite_database_service, image_uid)
            == ImageStatus.PRE_PROCESSING_FAILED
        )
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )

    def test_a_transient_failure_reading_on_the_last_attempt_fails_the_image(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.IMAGE_PRE_PROCESSING
        )
        image_uid = _add_image(
            sqlite_database_service, schema, stored, ImageStatus.DOWNLOADED
        )
        metadata_import_interface = decoy.mock(cls=MetadataImportInterface)
        decoy.when(
            metadata_import_interface.import_image_metadata(
                Anything(), Anything(), Anything(), Anything()
            )
        ).then_raise(TransientTaskError("Share unreachable"))

        # Act
        _download_and_pre_process(
            image_uid,
            sqlite_database_service,
            batch_service,
            schema_service,
            decoy.mock(cls=ImageImportInterface),
            metadata_import_interface,
            _not_retried,
            decoy.mock(cls=ReviewService),
        )

        # Assert
        assert (
            _image_status(sqlite_database_service, image_uid)
            == ImageStatus.PRE_PROCESSING_FAILED
        )
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )

    def test_an_image_that_no_longer_exists_is_not_processed(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
    ):
        # Arrange
        image_import_interface = decoy.mock(cls=ImageImportInterface)

        # Act
        _download_and_pre_process(
            uuid4(),
            sqlite_database_service,
            batch_service,
            schema_service,
            image_import_interface,
            decoy.mock(cls=MetadataImportInterface),
            _not_retried,
            decoy.mock(cls=ReviewService),
        )

        # Assert
        decoy.verify(image_import_interface.download(Anything(), Anything()), times=0)


@pytest.mark.integration
class TestPostProcessImage:
    def test_a_transient_failure_on_the_last_attempt_settles_the_batch(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        open_sessions: list[Session],
        batch_service: BatchService,
        schema_service: SchemaService,
        storage_service: StorageService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.IMAGE_POST_PROCESSING
        )
        image_uid = _add_image(
            sqlite_database_service, schema, stored, ImageStatus.PRE_PROCESSED
        )
        sessions_while_working: list[int] = []

        def export(image: Image, batch: Any, project: Any, task_id: str) -> Image:
            sessions_while_working.append(len(open_sessions))
            raise TransientTaskError("Processing share unreachable")

        image_export_interface = decoy.mock(cls=ImageExportInterface)
        decoy.when(
            image_export_interface.export(
                Anything(), Anything(), Anything(), task_id="1"
            )
        ).then_do(export)

        # Act
        _post_process(
            image_uid,
            sqlite_database_service,
            batch_service,
            schema_service,
            storage_service,
            image_export_interface,
            _not_retried,
        )

        # Assert
        assert sessions_while_working == [0]
        assert (
            _image_status(sqlite_database_service, image_uid)
            == ImageStatus.POST_PROCESSING_FAILED
        )
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
        )
        decoy.verify(storage_service.cleanup_processing_task(Anything(), "1"), times=1)

    def test_a_transient_failure_that_is_retried_sets_the_image_back(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        storage_service: StorageService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.IMAGE_POST_PROCESSING
        )
        image_uid = _add_image(
            sqlite_database_service, schema, stored, ImageStatus.PRE_PROCESSED
        )
        image_export_interface = decoy.mock(cls=ImageExportInterface)
        decoy.when(
            image_export_interface.export(
                Anything(), Anything(), Anything(), task_id="1"
            )
        ).then_raise(TransientTaskError("Processing share unreachable"))

        # Act & Assert
        with pytest.raises(TransientTaskError):
            _post_process(
                image_uid,
                sqlite_database_service,
                batch_service,
                schema_service,
                storage_service,
                image_export_interface,
                _retried,
            )
        assert (
            _image_status(sqlite_database_service, image_uid)
            == ImageStatus.PRE_PROCESSED
        )
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_POST_PROCESSING
        )

    def test_an_image_deleted_while_converted_fails_without_raising(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        storage_service: StorageService,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        """Writing what came of the conversion fails, and is handled as any
        other failure of the conversion: what was written is removed."""
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.IMAGE_POST_PROCESSING
        )
        image_uid = _add_image(
            sqlite_database_service, schema, stored, ImageStatus.PRE_PROCESSED
        )

        def export(image: Image, batch: Any, project: Any, task_id: str) -> Image:
            with sqlite_database_service.get_session() as session:
                session.delete(sqlite_database_service.get_image(session, image_uid))
            image.folder_path = str(tmp_path)
            return image

        image_export_interface = decoy.mock(cls=ImageExportInterface)
        decoy.when(
            image_export_interface.export(
                Anything(), Anything(), Anything(), task_id="1"
            )
        ).then_do(export)

        # Act
        _post_process(
            image_uid,
            sqlite_database_service,
            batch_service,
            schema_service,
            storage_service,
            image_export_interface,
            _not_retried,
        )

        # Assert
        decoy.verify(storage_service.cleanup_processing_task(Anything(), "1"), times=1)
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
        )


@pytest.mark.integration
class TestStoreBatchImagesToOutbox:
    @pytest.fixture(autouse=True)
    def image_export_interface(self, decoy: Decoy) -> None:
        self._image_export_interface = decoy.mock(cls=ImageExportInterface)

    def _store(
        self,
        batch_uid: UUID,
        database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        storage_service: StorageService,
        will_retry: Callable[[BaseException], bool],
    ) -> None:
        store_batch_images_to_outbox.func.__wrapped__(  # type: ignore[attr-defined]
            batch_uid=batch_uid,
            database_service=database_service,
            batch_service=batch_service,
            storage_service=storage_service,
            schema_service=schema_service,
            image_export_interface=self._image_export_interface,
            dicom_metadata_writer=DicomMetadataWriter(),
            will_retry=will_retry,
        )

    def test_a_transient_failure_on_the_last_attempt_fails_the_image(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        storage_service: StorageService,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        """Failed rather than left storing, so that the image can be retried
        through the route a failed image is retried through."""
        # Arrange
        stored = _add_batch(sqlite_database_service, schema, BatchStatus.IMAGE_STORING)
        image_uid = _add_image(
            sqlite_database_service,
            schema,
            stored,
            ImageStatus.POST_PROCESSED,
            folder_path=str(tmp_path),
        )
        decoy.when(
            storage_service.store_image_to_outbox(Anything(), Anything(), Anything())
        ).then_raise(TransientTaskError("Outbox unreachable"))

        # Act
        self._store(
            stored.batch_uid,
            sqlite_database_service,
            batch_service,
            schema_service,
            storage_service,
            _not_retried,
        )

        # Assert
        assert (
            _image_status(sqlite_database_service, image_uid)
            == ImageStatus.STORING_FAILED
        )
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.IMAGE_STORING
        )

    def test_a_transient_failure_that_is_retried_leaves_the_image_storing(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        storage_service: StorageService,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        # Arrange
        stored = _add_batch(sqlite_database_service, schema, BatchStatus.IMAGE_STORING)
        image_uid = _add_image(
            sqlite_database_service,
            schema,
            stored,
            ImageStatus.POST_PROCESSED,
            folder_path=str(tmp_path),
        )
        decoy.when(
            storage_service.store_image_to_outbox(Anything(), Anything(), Anything())
        ).then_raise(TransientTaskError("Outbox unreachable"))

        # Act & Assert
        with pytest.raises(TransientTaskError):
            self._store(
                stored.batch_uid,
                sqlite_database_service,
                batch_service,
                schema_service,
                storage_service,
                _retried,
            )
        assert _image_status(sqlite_database_service, image_uid) == ImageStatus.STORING

    def test_an_image_stored_by_an_attempt_that_did_not_record_it_is_recorded(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        storage_service: StorageService,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        """The files were written again into the outbox under new names, and
        the processing folder discarded, before the attempt could record it."""
        # Arrange
        stored = _add_batch(sqlite_database_service, schema, BatchStatus.IMAGE_STORING)
        processing = tmp_path.joinpath("processing", "PL1234-20-1")
        outbox = tmp_path.joinpath("outbox", "PL1234-20-1")
        image_uid = _add_image(
            sqlite_database_service,
            schema,
            stored,
            ImageStatus.STORING,
            folder_path=str(processing),
        )

        def recover_stored_image(project: Any, image: Image, dataset: Any) -> bool:
            image.folder_path = str(outbox)
            image.files = [
                ImageFile(uid=uuid4(), filename=filename)
                for filename in ("rewritten-1.dcm", "rewritten-2.dcm")
            ]
            image.metadata_digest = None
            return True

        decoy.when(
            storage_service.recover_stored_image(Anything(), Anything(), Anything())
        ).then_do(recover_stored_image)

        # Act
        self._store(
            stored.batch_uid,
            sqlite_database_service,
            batch_service,
            schema_service,
            storage_service,
            _not_retried,
        )

        # Assert
        with sqlite_database_service.get_session() as session:
            image = sqlite_database_service.get_image(session, image_uid)
            assert image.status == ImageStatus.STORED
            assert image.folder_path == str(outbox)
            assert sorted(file.filename for file in image.files) == [
                "rewritten-1.dcm",
                "rewritten-2.dcm",
            ]
            assert image.metadata_digest is None
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.COMPLETED
        )


@pytest.mark.integration
class TestProcessMetadataImport:
    def test_a_transient_failure_on_the_last_attempt_fails_the_batch(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        batch_service: BatchService,
        schema_service: SchemaService,
        schema: ExampleSchema,
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.METADATA_SEARCHING
        )
        metadata_import_interface = decoy.mock(cls=MetadataImportInterface)
        decoy.when(
            metadata_import_interface.search(Anything(), Anything(), Anything())
        ).then_raise(TransientTaskError("Source unreachable"))

        # Act
        process_metadata_import.func.__wrapped__(  # type: ignore[attr-defined]
            batch_uid=stored.batch_uid,
            search_parameters={},
            metadata_import_interface=metadata_import_interface,
            database_service=sqlite_database_service,
            batch_service=batch_service,
            item_service=decoy.mock(cls=ItemService),
            search_item_service=MetadataSearchItemService(sqlite_database_service),
            schema_service=schema_service,
            will_retry=_not_retried,
        )

        # Assert
        assert (
            _batch_status(sqlite_database_service, stored.batch_uid)
            == BatchStatus.FAILED
        )


@pytest.mark.integration
class TestStalledJobRecovery:
    @staticmethod
    def _job(task_name: str, **task_kwargs: Any) -> Job:
        return Job(
            id=1,
            queue="image_processing",
            lock=None,
            queueing_lock=None,
            task_name=task_name,
            task_kwargs=task_kwargs,
        )

    def test_an_image_that_no_longer_exists_has_nothing_to_reset(
        self, sqlite_database_service: DatabaseService
    ):
        # Arrange
        job = self._job("post_process_image", image_uid=str(uuid4()))

        # Act & Assert
        _reset_state_for_stalled_job(sqlite_database_service, job)

    def test_an_image_left_post_processing_is_set_back(
        self, sqlite_database_service: DatabaseService, schema: ExampleSchema
    ):
        # Arrange
        stored = _add_batch(
            sqlite_database_service, schema, BatchStatus.IMAGE_POST_PROCESSING
        )
        image_uid = _add_image(
            sqlite_database_service, schema, stored, ImageStatus.POST_PROCESSING
        )
        job = self._job("post_process_image", image_uid=str(image_uid))

        # Act
        _reset_state_for_stalled_job(sqlite_database_service, job)

        # Assert
        assert (
            _image_status(sqlite_database_service, image_uid)
            == ImageStatus.PRE_PROCESSED
        )

    @pytest.mark.asyncio
    async def test_a_job_that_fails_to_reset_does_not_stop_the_others(
        self, sqlite_database_service: DatabaseService
    ):
        # Arrange
        failing = self._job("post_process_image", image_uid="not-a-uid")
        other = self._job("process_metadata_import", batch_uid=str(uuid4()))
        retried: list[Job] = []

        class JobManager:
            async def get_stalled_jobs(self, seconds_since_heartbeat: float):
                return [failing, other]

            async def retry_job(self, job: Job) -> None:
                retried.append(job)

        app = SimpleNamespace(job_manager=JobManager())

        # Act
        await retry_stalled_jobs.func.__wrapped__(  # type: ignore[attr-defined]
            timestamp=0,
            database_service=sqlite_database_service,
            config=SimpleNamespace(stalled_worker_timeout=1),
            app=app,
        )

        # Assert
        assert retried == [failing, other]


@pytest.mark.unittest
class TestRetryCheck:
    @staticmethod
    def _job(attempts: int) -> Job:
        return Job(
            id=1,
            queue="default",
            lock=None,
            queueing_lock=None,
            task_name="task",
            attempts=attempts,
        )

    def test_a_transient_failure_before_the_last_attempt_is_retried(self):
        # Arrange
        will_retry = retry_check(_TRANSIENT_RETRY, self._job(attempts=0))

        # Act & Assert
        assert will_retry(TransientTaskError("Unreachable"))

    def test_a_transient_failure_on_the_last_attempt_is_not_retried(self):
        # Arrange
        assert _TRANSIENT_RETRY.max_attempts is not None
        will_retry = retry_check(
            _TRANSIENT_RETRY, self._job(attempts=_TRANSIENT_RETRY.max_attempts)
        )

        # Act & Assert
        assert not will_retry(TransientTaskError("Unreachable"))

    def test_any_other_failure_is_not_retried(self):
        # Arrange
        will_retry = retry_check(_TRANSIENT_RETRY, self._job(attempts=0))

        # Act & Assert
        assert not will_retry(ValueError("Unreadable"))

    def test_a_task_without_a_retry_strategy_is_not_retried(self):
        # Arrange
        will_retry = retry_check(None, self._job(attempts=0))

        # Act & Assert
        assert not will_retry(TransientTaskError("Unreachable"))
