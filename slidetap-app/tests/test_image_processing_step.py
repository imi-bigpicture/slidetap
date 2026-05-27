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

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from slidetap.image_processor.image_processing_step import ImageProcessingStep
from slidetap.model import Image, ImageFile, ImageFormat


class _NoopStep(ImageProcessingStep):
    def run(self, *args, **kwargs):
        raise NotImplementedError


@pytest.fixture
def image() -> Image:
    return Image(
        uid=uuid4(),
        identifier="img-1",
        dataset_uid=uuid4(),
        schema_uid=uuid4(),
        format=ImageFormat.OTHER_WSI,
        files=[ImageFile(uid=uuid4(), filename="CMU-1.vms")],
    )


@pytest.fixture
def step() -> ImageProcessingStep:
    return _NoopStep()


def test_open_wsidicomizer_propagates_body_exception(
    step: ImageProcessingStep, image: Image
) -> None:
    """Regression test for imi-bigpicture/slidetap#40.

    An exception raised inside the consumer's ``with _open_wsidicomizer(...)``
    block must propagate to the caller. Previously the surrounding
    ``try/except Exception/pass`` swallowed it silently, masking pre-process
    failures (e.g. imi-bigpicture/bigpicture-slidetap#20)."""
    wsi = MagicMock()
    with patch(
        "slidetap.image_processor.image_processing_step.WsiDicomizer.open",
        return_value=wsi,
    ):
        with pytest.raises(RuntimeError, match="boom"):
            with step._open_wsidicomizer(image, Path("/tmp")) as opened:
                assert opened is wsi
                raise RuntimeError("boom")

    wsi.close.assert_called_once()


def test_open_wsidicomizer_skips_failed_open_and_uses_next_file(
    step: ImageProcessingStep,
) -> None:
    """A failure opening file N must not prevent file N+1 from being tried."""
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
    good_wsi = MagicMock()

    def _open(image_path, **kwargs):
        if image_path.name == "broken.vms":
            raise OSError("cannot read")
        return good_wsi

    with patch(
        "slidetap.image_processor.image_processing_step.WsiDicomizer.open",
        side_effect=_open,
    ):
        with step._open_wsidicomizer(image, Path("/tmp")) as opened:
            assert opened is good_wsi

    good_wsi.close.assert_called_once()


def test_open_wsidicomizer_yields_none_when_no_file_opens(
    step: ImageProcessingStep, image: Image
) -> None:
    """When no file successfully opens, the contextmanager must yield ``None``
    (downstream callers check ``if wsi is None``)."""
    with patch(
        "slidetap.image_processor.image_processing_step.WsiDicomizer.open",
        side_effect=OSError("cannot read"),
    ):
        with step._open_wsidicomizer(image, Path("/tmp")) as opened:
            assert opened is None


def test_open_wsidicomizer_yields_none_when_image_has_no_files(
    step: ImageProcessingStep,
) -> None:
    image = Image(
        uid=uuid4(),
        identifier="img-empty",
        dataset_uid=uuid4(),
        schema_uid=uuid4(),
        format=ImageFormat.OTHER_WSI,
        files=[],
    )
    with step._open_wsidicomizer(image, Path("/tmp")) as opened:
        assert opened is None
