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

"""How the image processor runs its steps, and what it raises when one fails."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from slidetap_example import ExampleSchema

from slidetap.external_interfaces import TransientTaskError
from slidetap.image_processor import FinishingStep, ImageProcessingStep, ImageProcessor
from slidetap.model import Batch, Dataset, Image, ImageFormat, Project, RootSchema
from slidetap.services import SchemaService, StorageService


class FailingStep(ImageProcessingStep):
    def __init__(self, exception: Exception, calls: list[str]):
        self._exception = exception
        self._calls = calls
        super().__init__()

    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
        working_folder: Path,
        task_id: str,
    ) -> tuple[Path, Image]:
        self._calls.append("step")
        raise self._exception


@pytest.fixture()
def processed_image(dataset: Dataset, schema: ExampleSchema, tmp_path: Path) -> Image:
    return Image(
        uid=uuid4(),
        identifier="image identifier",
        dataset_uid=dataset.uid,
        schema_uid=schema.image_schema_uid,
        format=ImageFormat.OTHER_WSI,
        folder_path=str(tmp_path),
    )


@pytest.fixture()
def storage_service(decoy: Decoy) -> StorageService:
    return decoy.mock(cls=StorageService)


@pytest.fixture()
def schema_service(decoy: Decoy, schema: RootSchema) -> SchemaService:
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.root_of(Anything())).then_return(
        SimpleNamespace(schema=schema)
    )
    return schema_service


@pytest.mark.unittest
class TestImageProcessor:
    def test_a_transient_failure_of_a_step_is_raised_as_it_is(
        self,
        storage_service: StorageService,
        schema_service: SchemaService,
        processed_image: Image,
        batch: Batch,
        project: Project,
    ):
        """Raised as it is, so that the task is retried rather than failed."""
        # Arrange
        failure = TransientTaskError("Processing share unreachable")
        processor = ImageProcessor(
            storage_service, schema_service, [FailingStep(failure, [])]
        )

        # Act & Assert
        with pytest.raises(TransientTaskError) as raised:
            processor.run(processed_image, batch, project, "1")
        assert raised.value is failure

    def test_any_other_failure_of_a_step_names_the_step(
        self,
        storage_service: StorageService,
        schema_service: SchemaService,
        processed_image: Image,
        batch: Batch,
        project: Project,
    ):
        # Arrange
        failure = ValueError("Unreadable file")
        processor = ImageProcessor(
            storage_service, schema_service, [FailingStep(failure, [])]
        )

        # Act & Assert
        with pytest.raises(Exception, match="at step") as raised:
            processor.run(processed_image, batch, project, "1")
        assert not isinstance(raised.value, TransientTaskError)
        assert raised.value.__cause__ is failure

    def test_what_an_earlier_run_of_the_task_left_is_removed_first(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        schema_service: SchemaService,
        processed_image: Image,
        batch: Batch,
        project: Project,
    ):
        """A job recovered from a worker that died runs again under the same id,
        and would otherwise find its processing directory already there."""
        # Arrange
        task_id = str(uuid4())
        calls: list[str] = []
        decoy.when(storage_service.cleanup_processing_task(project, task_id)).then_do(
            lambda project, task_id: calls.append("cleanup")
        )
        processor = ImageProcessor(
            storage_service,
            schema_service,
            [FailingStep(ValueError("Unreadable file"), calls)],
        )

        # Act
        with pytest.raises(Exception, match="at step"):
            processor.run(processed_image, batch, project, task_id)

        # Assert
        assert calls == ["cleanup", "step"]


@pytest.mark.unittest
class TestFinishingStep:
    @pytest.mark.parametrize("remove_source", [True, False])
    def test_the_source_is_removed_through_storage_only_when_asked(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        schema: RootSchema,
        processed_image: Image,
        project: Project,
        tmp_path: Path,
        remove_source: bool,
    ):
        """Through storage, which removes a folder as well as a file, and only
        under the project's own folders."""
        # Arrange
        source = Path(processed_image.folder_path or "")
        processed = tmp_path.joinpath("processed")
        step = FinishingStep(remove_source=remove_source)

        # Act
        path, image = step.run(
            schema,
            storage_service,
            project,
            processed_image,
            processed,
            tmp_path.joinpath("working"),
            "1",
        )

        # Assert
        assert path == processed
        assert image.folder_path is None
        decoy.verify(
            storage_service.cleanup_image_source(project, image, source),
            times=1 if remove_source else 0,
        )

    def test_the_processed_image_is_not_removed_as_the_source(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        schema: RootSchema,
        processed_image: Image,
        project: Project,
        tmp_path: Path,
    ):
        """Where no step moved the image, the source is what is handed on."""
        # Arrange
        source = Path(processed_image.folder_path or "")
        step = FinishingStep(remove_source=True)

        # Act
        step.run(
            schema,
            storage_service,
            project,
            processed_image,
            source,
            tmp_path.joinpath("working"),
            "1",
        )

        # Assert
        decoy.verify(
            storage_service.cleanup_image_source(Anything(), Anything(), Anything()),
            times=0,
        )
