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

"""Tests for storing images, and for the storage failures storing them to a mount
that drops mid-operation must survive.

The file system operations are mocked: the semantics they are built on are pinned
in ``test_file_operations``, and what storing has to get right is which operations
it performs, in which order, and what it does to recover when one of them fails.
"""

import dataclasses
from pathlib import Path
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything, Captor

from slidetap.config import StorageConfig
from slidetap.external_interfaces.exceptions import TransientTaskError
from slidetap.model import Dataset, Image, ImageFormat, Project, RootSchema
from slidetap.services.database_service import DatabaseService
from slidetap.services.file_operations import FileOperations
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
def file_operations(decoy: Decoy) -> FileOperations:
    """File operations that succeed, on one file system, with nothing missing."""
    file_operations = decoy.mock(cls=FileOperations)
    decoy.when(file_operations.exists(Anything())).then_return(True)
    decoy.when(file_operations.same_filesystem(Anything(), Anything())).then_return(
        True
    )
    return file_operations


@pytest.fixture()
def database_service(decoy: Decoy) -> DatabaseService:
    """A database that is never reached: the folders here are already claimed."""
    return decoy.mock(cls=DatabaseService)


@pytest.fixture()
def storage_service(
    config: StorageConfig,
    database_service: DatabaseService,
    file_operations: FileOperations,
) -> StorageService:
    return StorageService(config, database_service, file_operations)


@pytest.fixture()
def project(project: Project) -> Project:
    """A project that has already claimed its folder.

    Claiming it is what ``TestStorageFolder`` covers; the tests here are about
    what is stored in the folder once there is one.
    """
    project.storage_folder = f"{project.name}.{project.uid}"
    return project


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
def processed_image(image: Image, config: StorageConfig) -> Image:
    """Image processed to a processing folder, ready to be stored."""
    processing = config.processing.joinpath("task id")
    image.folder_path = str(processing.joinpath("images", image.identifier))
    image.thumbnail_path = str(
        processing.joinpath("thumbnails", image.identifier + ".jpeg")
    )
    return image


@pytest.fixture()
def image_destination(
    storage_service: StorageService, project: Project, dataset: Dataset
) -> Path:
    return storage_service._project_images_outbox(project, dataset).joinpath(
        "image identifier"
    )


@pytest.fixture()
def thumbnail_destination(storage_service: StorageService, project: Project) -> Path:
    return storage_service._project_thumbnail_outbox(project).joinpath(
        "image identifier.jpeg"
    )


@pytest.mark.unittest
class TestStorageService:
    def test_store_image_to_outbox_renames_image_and_thumbnail_into_place(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
        image_destination: Path,
        thumbnail_destination: Path,
    ) -> None:
        """On one file system the image and thumbnail are renamed into place.

        A rename is atomic, so the image is either where it was or stored, and
        never part-way between.
        """
        # Arrange
        source_folder = Path(processed_image.folder_path)
        source_thumbnail = Path(processed_image.thumbnail_path)
        decoy.when(file_operations.exists(image_destination)).then_return(False)
        decoy.when(file_operations.exists(thumbnail_destination)).then_return(False)

        # Act
        storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert
        decoy.verify(
            file_operations.rename(source_folder, image_destination),
            file_operations.rename(source_thumbnail, thumbnail_destination),
        )
        assert processed_image.folder_path == str(image_destination)
        assert processed_image.thumbnail_path == str(thumbnail_destination)

    def test_store_image_to_outbox_renames_existing_destination_aside(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
        image_destination: Path,
    ) -> None:
        """An existing destination is renamed aside, and only removed once stored.

        A rename cannot replace an existing folder, and removing the destination
        first would leave neither the old nor the new image in place if the store
        then failed.
        """
        # Arrange
        source_folder = Path(processed_image.folder_path)
        aside = Captor()

        # Act
        storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert
        decoy.verify(
            file_operations.rename(image_destination, aside),
            file_operations.rename(source_folder, image_destination),
            file_operations.remove(Anything()),
        )
        decoy.verify(file_operations.remove(aside.value), times=1)

    def test_store_image_to_outbox_across_filesystems_copies_and_discards_source(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
        image_destination: Path,
    ) -> None:
        """Across file systems the image is copied beside its destination first.

        The source cannot be renamed across file systems, and is only discarded
        once the copy has been renamed into place.
        """
        # Arrange
        source_folder = Path(processed_image.folder_path)
        decoy.when(file_operations.same_filesystem(Anything(), Anything())).then_return(
            False
        )
        decoy.when(file_operations.exists(image_destination)).then_return(False)

        # Act
        storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert the copy is staged beside the destination, renamed into place, and
        # the source only discarded after.
        staged = Captor()
        discarded = Captor()
        decoy.verify(
            file_operations.copy(source_folder, staged),
            file_operations.rename(Anything(), image_destination),
            file_operations.rename(source_folder, discarded),
            file_operations.remove(Anything()),
        )
        decoy.verify(file_operations.rename(staged.value, image_destination), times=1)
        decoy.verify(file_operations.remove(discarded.value), times=1)

    def test_store_image_to_outbox_removes_staged_copy_when_copy_fails(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
        image_destination: Path,
    ) -> None:
        """A failed copy is removed, and the destination is not touched.

        The destination is only renamed aside once the source is staged, so a copy
        that fails part-way leaves both the source and the destination as they
        were, and the partial copy is removed.
        """
        # Arrange
        decoy.when(file_operations.same_filesystem(Anything(), Anything())).then_return(
            False
        )
        decoy.when(file_operations.copy(Anything(), Anything())).then_raise(DISCONNECT)

        # Act
        with pytest.raises(TransientTaskError):
            storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert the partial copy staged beside the destination is removed, and
        # that nothing was renamed into the destination.
        staged = Captor()
        decoy.verify(file_operations.remove(staged), times=1)
        decoy.verify(file_operations.rename(Anything(), image_destination), times=0)
        assert staged.value.parent == image_destination.parent
        assert staged.value.name.endswith(".tmp")

    def test_store_image_to_outbox_restores_destination_when_rename_fails(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
        image_destination: Path,
    ) -> None:
        """A failed rename into place restores the destination that was set aside."""
        # Arrange
        source_folder = Path(processed_image.folder_path)
        aside = Captor()
        decoy.when(file_operations.rename(source_folder, image_destination)).then_raise(
            DISCONNECT
        )

        # Act
        with pytest.raises(TransientTaskError):
            storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert the destination is renamed aside, and renamed back once the rename
        # into its place has failed.
        decoy.verify(file_operations.rename(image_destination, aside), times=1)
        decoy.verify(file_operations.rename(aside.value, image_destination), times=1)

    def test_store_image_to_outbox_of_stored_image_is_a_no_op(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
        image_destination: Path,
    ) -> None:
        """An image an earlier attempt stored, but did not record, is not stored again.

        A crash between the store and the commit leaves the image stored with its
        path still pointing into the processing directory. The retry finds the
        source gone and the destination in place, and records where it was stored.
        """
        # Arrange
        source_folder = Path(processed_image.folder_path)
        decoy.when(file_operations.exists(source_folder)).then_return(False)

        # Act
        storage_service.store_image_to_outbox(project, processed_image, dataset)

        # Assert
        assert processed_image.folder_path == str(image_destination)
        decoy.verify(file_operations.rename(source_folder, Anything()), times=0)

    def test_store_image_to_outbox_of_unreachable_image_raises_transient_error(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
    ) -> None:
        """An image on a dropped mount is not reported as stored.

        A path on a dropped mount reads as missing rather than raising, so an image
        that is there, but cannot be reached, is indistinguishable from one that has
        been stored, unless a source that is neither where it is expected nor
        already stored is raised on.
        """
        # Arrange
        source_folder = Path(processed_image.folder_path)
        decoy.when(file_operations.exists(Anything())).then_return(False)

        # Act & Assert
        with pytest.raises(TransientTaskError):
            storage_service.store_image_to_outbox(project, processed_image, dataset)
        assert processed_image.folder_path == str(source_folder), (
            "the image was recorded as stored while its mount was unreachable"
        )

    def test_store_image_to_outbox_raises_transient_error_when_outbox_is_unreachable(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        dataset: Dataset,
        processed_image: Image,
    ) -> None:
        """An outbox that cannot be created must be retried, not failed.

        The outbox folders are created as the image is stored, and a mount that is
        down fails that as any other file operation. It must be raised on as a
        transient failure, or the image is set as storing failed, which it cannot
        be retried from.
        """
        # Arrange
        decoy.when(file_operations.make_folder(Anything())).then_raise(DISCONNECT)

        # Act & Assert
        with pytest.raises(TransientTaskError):
            storage_service.store_image_to_outbox(project, processed_image, dataset)

    def test_store_image_to_processing_raises_transient_error_on_copy_failure(
        self,
        decoy: Decoy,
        storage_service: StorageService,
        file_operations: FileOperations,
        project: Project,
        image: Image,
        tmp_path: Path,
    ) -> None:
        """A failed copy must raise ``TransientTaskError``, not be swallowed.

        ``TransientTaskError`` is the only exception class the task retry strategy
        in ``tasks.py`` acts on (``retry_exceptions``), so an ``OSError`` from a
        dropped mount must be wrapped in it to be retried instead of recorded as a
        successful store.
        """
        # Arrange
        source = tmp_path.joinpath("source image")
        decoy.when(file_operations.copy(Anything(), Anything())).then_raise(DISCONNECT)

        # Act & Assert
        with pytest.raises(TransientTaskError):
            storage_service.store_image_to_processing(
                project, image, source, task_id="task id"
            )


@pytest.mark.integration
class TestStorageFolder:
    """The folder a project or dataset is stored in, and its claiming.

    Run against a real database rather than a mock: what these have to prove is
    that the claimed folder is written down and read back, and that a rename
    afterwards leaves it alone.
    """

    @pytest.fixture()
    def storage_service(
        self,
        config: StorageConfig,
        sqlite_database_service: DatabaseService,
        file_operations: FileOperations,
    ) -> StorageService:
        return StorageService(config, sqlite_database_service, file_operations)

    @pytest.fixture()
    def stored_project(
        self,
        sqlite_database_service: DatabaseService,
        project: Project,
        dataset: Dataset,
    ) -> Project:
        """A project, with its dataset, in the database and yet to claim."""
        project.storage_folder = None
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_dataset(session, dataset)
            sqlite_database_service.add_project(session, project)
        return project

    @pytest.fixture()
    def stored_dataset(
        self, sqlite_database_service: DatabaseService, dataset: Dataset
    ) -> Dataset:
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_dataset(session, dataset)
        return dataset

    def rename(
        self,
        database_service: DatabaseService,
        item: Project | Dataset,
        name: str,
    ) -> None:
        with database_service.get_session() as session:
            database_item = (
                database_service.get_project(session, item)
                if isinstance(item, Project)
                else database_service.get_dataset(session, item)
            )
            database_item.name = name
        item.name = name

    def test_project_folder_is_claimed_from_the_name(
        self,
        storage_service: StorageService,
        sqlite_database_service: DatabaseService,
        stored_project: Project,
    ) -> None:
        """The first claim gives the folder the project name gives it.

        A project that stored content before there was a column to write the
        folder down in thus claims the folder it is already stored in, and
        nothing on disk has to move.
        """
        # Act
        folder = storage_service.project_folder(stored_project)

        # Assert
        assert folder == f"{stored_project.name}.{stored_project.uid}"
        with sqlite_database_service.get_session() as session:
            database_project = sqlite_database_service.get_project(
                session, stored_project
            )
            assert database_project.storage_folder == folder

    def test_project_folder_survives_a_rename(
        self,
        storage_service: StorageService,
        sqlite_database_service: DatabaseService,
        stored_project: Project,
    ) -> None:
        """Renaming the project must not move where its content is stored."""
        # Arrange
        claimed = storage_service.project_outbox(stored_project)

        # Act
        self.rename(sqlite_database_service, stored_project, "renamed project")

        # Assert
        assert storage_service.project_outbox(stored_project) == claimed
        assert storage_service._project_download(stored_project).name == claimed.name
        assert storage_service._project_processing(stored_project).name == claimed.name

    def test_project_folder_claimed_by_another_worker_is_kept(
        self,
        storage_service: StorageService,
        sqlite_database_service: DatabaseService,
        stored_project: Project,
    ) -> None:
        """A claim finds the folder another worker wrote down, and keeps it.

        Two workers storing at once must agree on one folder, so a claim is a
        read of what is written down and only writes when nothing is.
        """
        # Arrange
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.get_project(
                session, stored_project
            ).storage_folder = "claimed elsewhere"

        # Act
        folder = storage_service.project_folder(stored_project)

        # Assert
        assert folder == "claimed elsewhere"

    def test_project_folder_of_project_not_in_database_is_not_claimed(
        self,
        storage_service: StorageService,
        project: Project,
    ) -> None:
        """A project being deleted has no row to write to, and is not written to.

        Its folder is still the one its name gives it, so cleanup removes the
        folder the project was stored in.
        """
        # Arrange
        project.storage_folder = None

        # Act
        folder = storage_service.project_folder(project)

        # Assert
        assert folder == f"{project.name}.{project.uid}"

    def test_dataset_folder_is_none_without_a_bundle_prefix(
        self, storage_service: StorageService, stored_dataset: Dataset
    ) -> None:
        """With no nesting configured there is no bundle folder to claim."""
        # Act & Assert
        assert storage_service.dataset_folder(stored_dataset) is None
        assert stored_dataset.storage_folder is None

    def test_dataset_folder_survives_a_rename(
        self,
        config: StorageConfig,
        sqlite_database_service: DatabaseService,
        file_operations: FileOperations,
        stored_dataset: Dataset,
        project: Project,
    ) -> None:
        """Renaming the dataset must not move the bundle its content is in."""
        # Arrange
        storage_service = StorageService(
            dataclasses.replace(config, bundle_prefix="BP-"),
            sqlite_database_service,
            file_operations,
        )
        claimed = storage_service.project_bundle(project, stored_dataset)
        assert claimed.name == "BP-dataset_name"

        # Act
        self.rename(sqlite_database_service, stored_dataset, "renamed dataset")

        # Assert
        assert storage_service.project_bundle(project, stored_dataset) == claimed
        assert storage_service.dataset_folder(stored_dataset) == "BP-dataset_name"
