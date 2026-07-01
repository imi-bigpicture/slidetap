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

"""Reproduction tests for silent data loss when the storage mount drops
mid-operation (e.g. a network share disconnect during ``shutil.copytree``/
``shutil.move``).

See ``.temp/slidetap network-share disconnect res.md`` H2/H3/H4.
"""

import datetime
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from slidetap.config import StorageConfig
from slidetap.external_interfaces.exceptions import TransientTaskError
from slidetap.model import Image, ImageFormat, Project
from slidetap.services.storage_service import StorageService


@pytest.mark.unittest
class TestStorageServiceDisconnect:
    @pytest.fixture
    def config(self, tmp_path: Path) -> StorageConfig:
        return StorageConfig(
            outbox=tmp_path / "storage",
            download=tmp_path / "download",
            processing=tmp_path / "processing",
        )

    @pytest.fixture
    def service(self, config: StorageConfig) -> StorageService:
        return StorageService(config)

    @pytest.fixture
    def project(self) -> Project:
        return Project(
            uid=uuid4(),
            name="proj",
            root_schema_uid=uuid4(),
            schema_uid=uuid4(),
            dataset_uid=uuid4(),
            created=datetime.datetime.now(),
        )

    @pytest.fixture
    def image(self) -> Image:
        return Image(
            uid=uuid4(),
            identifier="img-1",
            dataset_uid=uuid4(),
            schema_uid=uuid4(),
            format=ImageFormat.OTHER_WSI,
        )

    def test_move_folder_raises_transient_error_on_copy_failure(
        self, service: StorageService, project: Project, image: Image, tmp_path: Path
    ) -> None:
        """Regression test for H2 (silent swallow) and H1 (missight
        misclassification as permanent failure).

        ``_move_folder`` previously wrapped ``shutil.copytree``/
        ``shutil.move`` in a bare ``try/except Exception: log`` and then
        unconditionally returned the target path -- a mid-copy ``OSError``
        (share disconnect, stale NFS handle) was silently swallowed and
        reported as a successful store. It must now propagate, and as a
        ``TransientTaskError`` specifically, since that is the only
        exception class the Procrastinate retry strategy in ``tasks.py``
        acts on (see ``retry_exceptions=[TransientTaskError]``).
        """
        src = tmp_path / "src_image"
        src.mkdir()
        (src / "slide.dcm").write_bytes(b"dicom-bytes")

        with patch(
            "slidetap.services.storage_service.shutil.copytree",
            side_effect=OSError(107, "Transport endpoint is not connected"),
        ):
            with pytest.raises(TransientTaskError):
                service.store_processed_image(project, image, src, task_id="task-1")

    def test_publish_processed_images_preserves_dest_when_move_fails(
        self, service: StorageService, project: Project, image: Image, tmp_path: Path
    ) -> None:
        """Regression test for H4: ``publish_processed_images`` previously
        removed the existing destination folder with ``shutil.rmtree`` and
        only then called ``shutil.move``. If the share dropped between the
        two calls, the destination was gone and the source was never moved
        -- the image was lost with no exception surfacing to the caller's
        retry machinery. The destination must now survive a failed move
        (old content is renamed aside and restored, never deleted before
        the move succeeds).
        """
        final_images = service._project_images_outbox(project)
        dest = final_images / "img-1"
        dest.mkdir()
        (dest / "old.dcm").write_bytes(b"old-bytes")

        src = tmp_path / "processing_image"
        src.mkdir()
        (src / "slide.dcm").write_bytes(b"new-bytes")
        image.folder_path = str(src)

        with patch(
            "slidetap.services.storage_service.shutil.move",
            side_effect=OSError(107, "Transport endpoint is not connected"),
        ):
            with pytest.raises(TransientTaskError):
                service.publish_processed_images(project, [image])

        assert (dest / "old.dcm").exists(), "old destination content was lost"
        assert src.exists(), "source was consumed despite failed move"
