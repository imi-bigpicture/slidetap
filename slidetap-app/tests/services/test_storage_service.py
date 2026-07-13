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

"""Tests for storing images to the outbox, and for the storage failures that storing
them to a storage mount that drops mid-operation must survive."""

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from slidetap.config import StorageConfig
from slidetap.external_interfaces.exceptions import TransientTaskError
from slidetap.model import Dataset, Image, ImageFormat, Project, RootSchema
from slidetap.services.storage_service import StorageService

DISCONNECT = OSError(107, "Transport endpoint is not connected")


@pytest.fixture()
def config(tmp_path: Path) -> StorageConfig:
    return StorageConfig(
        outbox=tmp_path.joinpath("storage"),
        download=tmp_path.joinpath("download"),
        processing=tmp_path.joinpath("processing"),
    )


@pytest.fixture()
def storage_service(config: StorageConfig) -> StorageService:
    return StorageService(config)


@pytest.fixture()
def image(dataset: Dataset, schema: RootSchema) -> Image:
    return Image(
        uid=uuid4(),
        identifier="image identifier",
        dataset_uid=dataset.uid,
        schema_uid=schema.image_schema_uid,
        format=ImageFormat.OTHER_WSI,
    )


@pytest.fixture()
def processed_image(image: Image, tmp_path: Path) -> Image:
    """Image processed to a processing folder, ready to be stored."""
    folder = tmp_path.joinpath("processing", image.identifier)
    folder.mkdir(parents=True)
    folder.joinpath("slide.dcm").write_bytes(b"new bytes")
    thumbnail = tmp_path.joinpath("processing", image.identifier + ".jpeg")
    thumbnail.write_bytes(b"new thumbnail bytes")
    image.folder_path = str(folder)
    image.thumbnail_path = str(thumbnail)
    return image


@pytest.fixture()
def stored_image_folder(
    storage_service: StorageService, project: Project, dataset: Dataset
) -> Path:
    """Folder of a previously stored image, to be stored over."""
    folder = storage_service._project_images_outbox(project, dataset).joinpath(
        "image identifier"
    )
    folder.mkdir()
    folder.joinpath("old.dcm").write_bytes(b"old bytes")
    return folder


@pytest.mark.unittest
class TestStorageService:
    def test_store_image_to_processing_raises_transient_error_on_copy_failure(
        self,
        storage_service: StorageService,
        project: Project,
        image: Image,
        tmp_path: Path,
    ) -> None:
        """A failed copy must raise ``TransientTaskError``, not be swallowed.

        ``TransientTaskError`` is the only exception class the task retry
        strategy in ``tasks.py`` acts on (``retry_exceptions``), so an
        ``OSError`` from a share disconnect must be wrapped in it to be retried
        instead of recorded as a successful store.
        """
        # Arrange
        source = tmp_path.joinpath("source image")
        source.mkdir(parents=True)
        source.joinpath("slide.dcm").write_bytes(b"dicom bytes")
        copy_failure = patch(
            "slidetap.services.storage_service.shutil.copytree",
            side_effect=DISCONNECT,
        )

        # Act & Assert
        with copy_failure, pytest.raises(TransientTaskError):
            storage_service.store_image_to_processing(
                project, image, source, task_id="task id"
            )

    def test_store_image_to_outbox_stores_folder_and_thumbnail(
        self,
        storage_service: StorageService,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
    ) -> None:
        """Storing must move both the image folder and the thumbnail."""
        # Arrange
        images_outbox = storage_service._project_images_outbox(project, dataset)
        thumbnails_outbox = storage_service._project_thumbnail_outbox(project)
        source_folder = Path(processed_image.folder_path)
        source_thumbnail = Path(processed_image.thumbnail_path)

        # Act
        storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert
        folder = images_outbox.joinpath("image identifier")
        thumbnail = thumbnails_outbox.joinpath("image identifier.jpeg")
        assert processed_image.folder_path == str(folder)
        assert processed_image.thumbnail_path == str(thumbnail)
        assert folder.joinpath("slide.dcm").read_bytes() == b"new bytes"
        assert thumbnail.read_bytes() == b"new thumbnail bytes"
        assert not source_folder.exists()
        assert not source_thumbnail.exists()

    def test_store_image_to_outbox_across_filesystems_discards_source(
        self,
        storage_service: StorageService,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
    ) -> None:
        """Storing across filesystems must copy, and discard the source after.

        The source cannot be renamed across filesystems, so it is copied next to
        the destination and the copy renamed into place. The source is only
        removed once the copy is stored.
        """
        # Arrange
        images_outbox = storage_service._project_images_outbox(project, dataset)
        thumbnails_outbox = storage_service._project_thumbnail_outbox(project)
        source_folder = Path(processed_image.folder_path)
        other_filesystem = patch.object(
            StorageService, "_same_filesystem", return_value=False
        )

        # Act
        with other_filesystem:
            storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert
        folder = images_outbox.joinpath("image identifier")
        thumbnail = thumbnails_outbox.joinpath("image identifier.jpeg")
        assert folder.joinpath("slide.dcm").read_bytes() == b"new bytes"
        assert thumbnail.read_bytes() == b"new thumbnail bytes"
        assert not source_folder.exists(), "copied source was not discarded"
        assert [path.name for path in images_outbox.iterdir()] == ["image identifier"]
        assert [path.name for path in thumbnails_outbox.iterdir()] == [
            "image identifier.jpeg"
        ]

    def test_store_image_to_outbox_preserves_destination_when_staging_fails(
        self,
        storage_service: StorageService,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
        stored_image_folder: Path,
    ) -> None:
        """A failed staging copy must leave source and destination as they were.

        Staging the source across filesystems copies it, and a copy failing
        part-way leaves a partial staged copy behind. The destination is only
        renamed aside once the source is staged, so a failure to stage it must
        leave the destination untouched and the partial copy removed.
        """
        # Arrange
        images_outbox = storage_service._project_images_outbox(project, dataset)
        source_folder = Path(processed_image.folder_path)

        def copy_partially_then_fail(source: Path, destination: Path) -> None:
            destination.mkdir(parents=True)
            destination.joinpath("slide.dcm").write_bytes(b"partial bytes")
            raise DISCONNECT

        other_filesystem = patch.object(
            StorageService, "_same_filesystem", return_value=False
        )
        copy_failure = patch(
            "slidetap.services.storage_service.shutil.copytree",
            side_effect=copy_partially_then_fail,
        )

        # Act
        with other_filesystem, copy_failure, pytest.raises(TransientTaskError):
            storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert
        assert stored_image_folder.joinpath("old.dcm").read_bytes() == b"old bytes", (
            "old destination content was lost"
        )
        assert source_folder.joinpath("slide.dcm").read_bytes() == b"new bytes", (
            "source was consumed despite failed store"
        )
        assert [path.name for path in images_outbox.iterdir()] == [
            "image identifier"
        ], "partial staged copy was left behind"

    def test_store_image_to_outbox_restores_destination_when_rename_fails(
        self,
        storage_service: StorageService,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
        stored_image_folder: Path,
    ) -> None:
        """A failed rename into place must restore the destination.

        The destination is renamed aside before the source is renamed into its
        place, and must be restored if that rename fails. The source is renamed,
        which is atomic, so it is left where the paths on record say it is.
        """
        # Arrange
        images_outbox = storage_service._project_images_outbox(project, dataset)
        source_folder = Path(processed_image.folder_path)
        rename = Path.rename
        storing_fails = True

        def rename_failing_store(self: Path, target: Path) -> Path:
            nonlocal storing_fails
            if Path(target) == stored_image_folder and storing_fails:
                storing_fails = False
                raise DISCONNECT
            return rename(self, target)

        rename_failure = patch.object(Path, "rename", new=rename_failing_store)

        # Act
        with rename_failure, pytest.raises(TransientTaskError):
            storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert
        assert stored_image_folder.joinpath("old.dcm").read_bytes() == b"old bytes", (
            "old destination content was lost"
        )
        assert source_folder.joinpath("slide.dcm").read_bytes() == b"new bytes", (
            "source was consumed despite failed store"
        )
        assert [path.name for path in images_outbox.iterdir()] == [
            "image identifier"
        ], "destination was not restored in place"

    def test_store_image_to_outbox_records_store_that_was_not_recorded(
        self,
        storage_service: StorageService,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
    ) -> None:
        """A store that was not recorded must be recorded by the retry.

        A crash between the move and the commit leaves the image stored, but not
        set as stored, and its path still pointing into the processing directory.
        The retry finds the source gone and the destination in place, and records
        where it was stored.
        """
        # Arrange
        images_outbox = storage_service._project_images_outbox(project, dataset)
        folder = images_outbox.joinpath("image identifier")
        Path(processed_image.folder_path).rename(folder)

        # Act
        storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert
        assert processed_image.folder_path == str(folder)
        assert folder.joinpath("slide.dcm").read_bytes() == b"new bytes"

    def test_store_image_to_outbox_raises_transient_error_on_missing_source(
        self,
        storage_service: StorageService,
        project: Project,
        dataset: Dataset,
        image: Image,
        tmp_path: Path,
    ) -> None:
        """A source that cannot be found must not be stored as a no-op.

        A path on an unreachable filesystem reads as missing rather than raising,
        so a source that is neither where it is expected nor already stored
        must be raised on rather than reported as stored.
        """
        # Arrange
        image.folder_path = str(tmp_path.joinpath("processing", "image identifier"))

        # Act & Assert
        with pytest.raises(TransientTaskError):
            storage_service.store_image_to_outbox(project, image, dataset)
