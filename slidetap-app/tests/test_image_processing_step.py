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

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from decoy import Decoy
from wsidicom.metadata import Study
from wsidicomizer import WsiDicomizer
from wsidicomizer.metadata import WsiDicomizerMetadata

from slidetap.config import DicomizationConfig
from slidetap.external_interfaces.dicom_metadata_producer import (
    DicomMetadataProducer,
)
from slidetap.image_processor.dicom_metadata import DicomMetadataWriter
from slidetap.image_processor.image_processing_step import (
    DicomProcessingStep,
    ImageProcessingStep,
)
from slidetap.model import Image, ImageFile, ImageFormat, Project, RootSchema
from slidetap.services import StorageService
from tests.download_test_images import image_paths


class _NoopStep(ImageProcessingStep):
    def run(self, *args, **kwargs):
        raise NotImplementedError


@pytest.mark.unittest
class TestOpenWsidicomizer:
    @pytest.fixture
    def image(self) -> Image:
        return Image(
            uid=uuid4(),
            identifier="img-1",
            dataset_uid=uuid4(),
            schema_uid=uuid4(),
            format=ImageFormat.OTHER_WSI,
            files=[ImageFile(uid=uuid4(), filename="CMU-1.vms")],
        )

    @pytest.fixture
    def step(self) -> ImageProcessingStep:
        return _NoopStep()

    def test_open_wsidicomizer_propagates_body_exception(
        self, decoy: Decoy, step: ImageProcessingStep, image: Image, tmp_path: Path
    ) -> None:
        """Regression test for imi-bigpicture/slidetap#40.

        An exception raised inside the consumer's ``with _open_wsidicomizer(...)``
        block must propagate to the caller. Previously the surrounding
        ``try/except Exception/pass`` swallowed it silently, masking pre-process
        failures (e.g. imi-bigpicture/bigpicture-slidetap#20)."""
        # Arrange
        wsi = decoy.mock(cls=WsiDicomizer)

        # Act / Assert
        with (
            patch(
                "slidetap.image_processor.image_processing_step.WsiDicomizer.open",
                return_value=wsi,
            ),
            pytest.raises(RuntimeError, match="boom"),
            step._open_wsidicomizer(image, tmp_path) as opened,
        ):
            assert opened is wsi
            raise RuntimeError("boom")

        decoy.verify(wsi.close(), times=1)

    def test_open_wsidicomizer_skips_failed_open_and_uses_next_file(
        self, decoy: Decoy, step: ImageProcessingStep, tmp_path: Path
    ) -> None:
        """A failure opening file N must not prevent file N+1 from being tried."""
        # Arrange
        image = Image(
            uid=uuid4(),
            identifier="img-2",
            dataset_uid=uuid4(),
            schema_uid=uuid4(),
            format=ImageFormat.OTHER_WSI,
            files=[
                ImageFile(uid=uuid4(), filename="broken.vms"),
                ImageFile(uid=uuid4(), filename="good.vms"),
            ],
        )
        good_wsi = decoy.mock(cls=WsiDicomizer)

        def _open(image_path, **kwargs):
            if image_path.name == "broken.vms":
                raise OSError("cannot read")
            return good_wsi

        # Act / Assert
        with (
            patch(
                "slidetap.image_processor.image_processing_step.WsiDicomizer.open",
                side_effect=_open,
            ),
            step._open_wsidicomizer(image, tmp_path) as opened,
        ):
            assert opened is good_wsi

        decoy.verify(good_wsi.close(), times=1)

    def test_open_wsidicomizer_yields_none_when_no_file_opens(
        self, step: ImageProcessingStep, image: Image, tmp_path: Path
    ) -> None:
        """When no file successfully opens, the contextmanager must yield ``None``
        (downstream callers check ``if wsi is None``)."""
        # Arrange

        # Act / Assert
        with (
            patch(
                "slidetap.image_processor.image_processing_step.WsiDicomizer.open",
                side_effect=OSError("cannot read"),
            ),
            step._open_wsidicomizer(image, tmp_path) as opened,
        ):
            assert opened is None

    def test_open_wsidicomizer_yields_none_when_image_has_no_files(
        self, step: ImageProcessingStep, tmp_path: Path
    ) -> None:
        # Arrange
        image = Image(
            uid=uuid4(),
            identifier="img-empty",
            dataset_uid=uuid4(),
            schema_uid=uuid4(),
            format=ImageFormat.OTHER_WSI,
            files=[],
        )

        # Act / Assert
        with step._open_wsidicomizer(image, tmp_path) as opened:
            assert opened is None


class StudyProducer(DicomMetadataProducer):
    """Puts a study identifier in, as a producer puts in what the items say."""

    def __init__(self, study_identifier: str):
        self._study_identifier = study_identifier

    def create(
        self, schema: RootSchema, image: Image, base: WsiDicomizerMetadata
    ) -> WsiDicomizerMetadata:
        return replace(base, study=Study(identifier=self._study_identifier))


@pytest.mark.integration
@pytest.mark.skipif(
    not image_paths()[0].exists(),
    reason="Test images not found. Run `uv run python tests/download_test_images.py`.",
)
class TestDicomProcessingStepDigest:
    """The digest taken when an image is converted is compared with the one
    taken when it is stored, to move the files rather than write them again
    where nothing has changed."""

    @pytest.fixture
    def slide(self) -> Path:
        return image_paths()[0]

    @pytest.fixture
    def writer(self) -> DicomMetadataWriter:
        return DicomMetadataWriter()

    @pytest.fixture
    def image(self, slide: Path, writer: DicomMetadataWriter) -> Image:
        # What the file said about itself, kept as the import keeps it.
        with WsiDicomizer.open(slide) as wsi:
            source_metadata = writer.source_metadata(wsi.metadata)
        assert source_metadata is not None
        return Image(
            uid=uuid4(),
            identifier="img-1",
            dataset_uid=uuid4(),
            schema_uid=uuid4(),
            format=ImageFormat.OTHER_WSI,
            files=[ImageFile(uid=uuid4(), filename=slide.name)],
            source_metadata=source_metadata,
        )

    def convert(
        self,
        decoy: Decoy,
        image: Image,
        slide: Path,
        working_folder: Path,
        writer: DicomMetadataWriter,
    ) -> tuple[RootSchema, Image]:
        schema = decoy.mock(cls=RootSchema)
        step = DicomProcessingStep(
            DicomizationConfig(levels=[-1]),
            StudyProducer("CASE-1"),
            writer,
        )
        _, converted = step.run(
            schema,
            decoy.mock(cls=StorageService),
            decoy.mock(cls=Project),
            image,
            slide.parent,
            working_folder,
            "task",
        )
        return schema, converted

    def test_the_digest_is_the_one_storing_takes_when_nothing_has_changed(
        self,
        decoy: Decoy,
        image: Image,
        slide: Path,
        tmp_path: Path,
        writer: DicomMetadataWriter,
    ):
        # Arrange
        schema, converted = self.convert(decoy, image, slide, tmp_path, writer)
        base = writer.recorded(converted.source_metadata)
        assert base is not None

        # Act
        digest = writer.digest(StudyProducer("CASE-1").create(schema, converted, base))

        # Assert
        assert converted.metadata_digest is not None
        assert digest == converted.metadata_digest

    def test_the_digest_differs_from_the_one_storing_takes_when_the_items_changed(
        self,
        decoy: Decoy,
        image: Image,
        slide: Path,
        tmp_path: Path,
        writer: DicomMetadataWriter,
    ):
        # Arrange
        schema, converted = self.convert(decoy, image, slide, tmp_path, writer)
        base = writer.recorded(converted.source_metadata)
        assert base is not None

        # Act
        digest = writer.digest(StudyProducer("CASE-2").create(schema, converted, base))

        # Assert
        assert digest != converted.metadata_digest
