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

"""Storing images and metadata to outbox."""

import json
import logging
import re
import shutil
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from slidetap.config import StorageConfig
from slidetap.external_interfaces.exceptions import TransientTaskError
from slidetap.model import Dataset, Image, Project
from slidetap.services.file_operations import FileOperations


class StorageService:
    """Class for storing images and metadata to outbox folder."""

    def __init__(self, config: StorageConfig, file_operations: FileOperations):
        """Create a storage for storing images and metadata.

        Parameters
        ----------
        config: StorageConfig
            Configuration of the folders to store in.
        file_operations: FileOperations
            File operations to store with.
        """
        self._config = config
        self._file_operations = file_operations
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def outbox(self) -> Path:
        return self._config.outbox

    def store_thumbnail(
        self,
        project: Project,
        image: Image,
        thumbnail: bytes,
        use_pseudonyms: bool = False,
    ) -> Path:
        """Store thumbnail for image in project's thumbnail folder.

        Parameters
        ----------
        image: Image
            Image to store thumbnail for.
        thumbnail: bytes
            Thumbnail to store.

        Returns
        ----------
        Path
            Thumbnail path.

        """
        thumbnails_folder = self._project_thumbnail_outbox(project)
        if use_pseudonyms:
            if image.pseudonym is None:
                raise ValueError("Image does not have a pseudonym.")
            name = image.pseudonym
        else:
            name = image.identifier
        thumbnail_path = thumbnails_folder.joinpath(name + ".jpeg")
        self._make_folder(thumbnail_path.parent)
        self._logger.info(f"Storing thumbnail for {image.uid} to {thumbnail_path}.")
        with open(thumbnail_path, "wb") as thumbnail_file:
            thumbnail_file.write(thumbnail)
        return thumbnail_path

    def store(
        self,
        project: Project,
        data: dict[str | Path, StringIO | BytesIO],
        dataset: Dataset,
    ):
        """Store data in the dataset's bundle folder.

        Parameters
        ----------
        project: Project
            Project to store data for.
        data: dict[str | Path, StringIO | BytesIO]
            Data to store.
        dataset: Dataset
            Dataset the data belongs to; determines the bundle folder.
        """
        outbox = self.project_bundle(project, dataset)
        for path, stream in data.items():
            full_path = outbox.joinpath(path)
            self._make_folder(full_path.parent)
            self._logger.info(f"Storing {path} to {full_path}.")
            if isinstance(stream, StringIO):
                with open(full_path, "w") as file:
                    stream.seek(0)
                    shutil.copyfileobj(stream, file)
            else:
                with open(full_path, "wb") as file:
                    stream.seek(0)
                    shutil.copyfileobj(stream, file)

    def store_metadata(self, project: Project, metadata: dict[str | Path, StringIO]):
        """Store metadata in project's metadata folder

        Parameters
        ----------
        project: Project
            Project to store metadata for.
        metadata: dict[str | Path, TextIOWrapper]
            Metadata to store.
        """
        metadata_folder = self._project_metadata_outbox(project)
        for path, stream in metadata.items():
            full_path = metadata_folder.joinpath(path)
            self._make_folder(full_path.parent)
            self._logger.info(f"Storing metadata to {full_path}.")
            with open(full_path, "w") as metadata_file:
                stream.seek(0)
                shutil.copyfileobj(stream, metadata_file)

    def create_download_image_path(self, project: Project, image: Image) -> Path:
        """Get image storage path for download."""
        project_folder = self._project_download(project)
        folder = project_folder.joinpath(image.identifier)
        self._logger.info(f"Creating image download path {folder}.")
        self._make_folder(folder)
        return folder

    def cleanup_download_image_path(self, project: Project, image: Image):
        """Cleanup image storage path for download."""
        project_folder = self._project_download(project)
        self._remove_path(project_folder.joinpath(image.identifier))

    def store_pseudonyms(self, project: Project, pseudonyms: dict[str, dict[str, Any]]):
        """Store pseudonyms for project."""
        pseudonym_folder = self._project_pseudonym_outbox(project)
        pseudonym_path = pseudonym_folder.joinpath("pseudonyms.json")
        self._make_folder(pseudonym_path.parent)
        with open(pseudonym_path, "w") as pseudonym_file:
            json.dump(pseudonyms, pseudonym_file, indent=4)

    def cleanup_project(self, project: Project):
        """Remove project folder."""
        project_folder = self.project_outbox(project)
        self._remove_path(project_folder)
        download_folder = self._project_download(project)
        self._remove_path(download_folder)
        processing_folder = self._project_processing(project)
        self._remove_path(processing_folder)

    def cleanup_metadata(self, project: Project, dataset: Dataset):
        """Remove the metadata folders from the dataset bundle.

        These are ``metadata_path`` plus ``additional_metadata_paths``. Images
        are stored separately, are never among them, and so are preserved.
        """
        bundle = self.project_bundle(project, dataset)
        folders = (
            self._config.metadata_path,
            *self._config.additional_metadata_paths,
        )
        for folder in folders:
            self._remove_path(bundle.joinpath(folder))

    def cleanup_pseudonyms(self, project: Project):
        """Remove pseudonyms for project."""
        pseudonym_folder = self._project_pseudonym_outbox(project)
        self._remove_path(pseudonym_folder)

    def project_outbox(self, project: Project) -> Path:
        return self.outbox.joinpath(project.name + "." + str(project.uid))

    def dataset_folder(self, dataset: Dataset) -> str | None:
        """Name of the per-dataset bundle folder, or None for no nesting.

        When the storage config sets a bundle prefix, the folder is
        ``<prefix><alias>``, where the alias is the dataset name made path-safe:
        any run of characters outside ``[A-Za-z0-9._-]`` is collapsed to a
        single underscore, and a leading copy of the prefix is stripped to avoid
        doubling it. Raises ``ValueError`` if the name has no usable characters.
        """
        prefix = self._config.bundle_prefix
        if prefix is None:
            return None
        name = re.sub(rf"(?i)^{re.escape(prefix)}", "", dataset.name)
        alias = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
        if not alias:
            raise ValueError(
                f"Dataset name {dataset.name!r} has no characters usable for a "
                "bundle folder (letters, digits, '.', '_' and '-')."
            )
        return prefix + alias

    def project_bundle(self, project: Project, dataset: Dataset) -> Path:
        """Return the folder that bundle content (images, metadata) is stored in.

        This is the project outbox, optionally nested in the per-dataset bundle
        folder from the storage config. Supporting folders (thumbnails,
        pseudonyms) stay at the project outbox root and do not use this.
        """
        outbox = self.project_outbox(project)
        folder = self.dataset_folder(dataset)
        return outbox.joinpath(folder) if folder else outbox

    def _project_download(self, project: Project) -> Path:
        return self._config.download.joinpath(project.name + "." + str(project.uid))

    def store_image_to_processing(
        self,
        project: Project,
        image: Image,
        path: Path,
        task_id: str,
        use_pseudonyms: bool = False,
    ) -> Path:
        """Copy image to a task-specific processing directory (not outbox)."""
        project_folder = self._task_processing_images(project, task_id)
        if use_pseudonyms:
            if image.pseudonym is None:
                raise ValueError("Image does not have a pseudonym.")
            folder_name = image.pseudonym
        else:
            folder_name = image.identifier
        self._logger.info(
            f"Storing processed image {image.identifier} to "
            f"{project_folder.joinpath(folder_name)}."
        )
        return self._copy_folder(path, project_folder, folder_name)

    def store_thumbnail_to_processing(
        self,
        project: Project,
        image: Image,
        thumbnail: bytes,
        task_id: str,
        use_pseudonyms: bool = False,
    ) -> Path:
        """Store thumbnail in a task-specific processing directory (not outbox)."""
        thumbnails_folder = self._task_processing_thumbnails(project, task_id)
        if use_pseudonyms:
            if image.pseudonym is None:
                raise ValueError("Image does not have a pseudonym.")
            name = image.pseudonym
        else:
            name = image.identifier
        thumbnail_path = thumbnails_folder.joinpath(name + ".jpeg")
        self._make_folder(thumbnail_path.parent)
        self._logger.info(
            f"Storing processed thumbnail for {image.uid} to {thumbnail_path}."
        )
        with open(thumbnail_path, "wb") as thumbnail_file:
            thumbnail_file.write(thumbnail)
        return thumbnail_path

    def store_image_to_outbox(
        self, project: Project, image: Image, dataset: Dataset
    ) -> None:
        """Move processed image and thumbnail from processing dir to outbox.

        Reads the image's current ``folder_path`` and ``thumbnail_path`` (which
        point into a task-specific processing directory) and moves them to the
        final outbox location. Updates the paths in-place. The image goes into the
        dataset bundle folder, the thumbnail stays at the outbox root.

        The caller is expected to persist the paths and set the image as stored
        before storing the next image, so that the paths on record follow the data
        on disk, and a retry passes over the images it has already stored.

        Parameters
        ----------
        project: Project
            Project the image belongs to.
        image: Image
            Image to store.
        dataset: Dataset
            Dataset the image is bundled in.
        """
        if image.folder_path is not None:
            image.folder_path = str(
                self._move_to_outbox(
                    Path(image.folder_path),
                    self._project_images_outbox(project, dataset),
                )
            )
        if image.thumbnail_path is not None:
            image.thumbnail_path = str(
                self._move_to_outbox(
                    Path(image.thumbnail_path), self._project_thumbnail_outbox(project)
                )
            )

    def _move_to_outbox(self, source: Path, destination_folder: Path) -> Path:
        """Move source file or folder into destination folder.

        The source is only ever renamed into its destination, and is otherwise
        left where the paths on record say it is: on the same filesystem it is
        renamed straight into place, and on another filesystem it is copied next
        to the destination and the copy renamed into place, the source only being
        removed once the copy is stored.

        A failure or a crash at any point thus leaves the source where it was, or
        the destination stored, and never the data in neither place. Storing an
        already stored source is a no-op, so that a retry can pass over the images
        the failed attempt stored.

        Parameters
        ----------
        source: Path
            File or folder to move.
        destination_folder: Path
            Folder to move the source into.

        Returns
        -------
        Path
            Path of the moved source, or of the already stored destination.

        Raises
        ------
        TransientTaskError
            If the source could not be stored, or if neither the source nor the
            destination can be found.
        """
        destination = destination_folder.joinpath(source.name)
        if not self._file_operations.exists(source):
            if self._file_operations.exists(destination):
                # The source was moved by an attempt that failed before it could
                # record where it stored it.
                return destination
            # A path on an unreachable filesystem reads as missing rather than
            # raising, so a source that has not been stored is not necessarily
            # gone.
            raise TransientTaskError(f"Neither {source} nor {destination} exists")

        if self._file_operations.same_filesystem(source, destination_folder):
            self._rename_into_place(source, destination)
            return destination

        staged = destination.with_name(f"{destination.name}.{uuid4()}.staged")
        try:
            self._file_operations.copy(source, staged)
        except OSError as exception:
            self._remove_path(staged)
            raise TransientTaskError(
                f"Failed to stage {source} at {staged}"
            ) from exception
        try:
            self._rename_into_place(staged, destination)
        except TransientTaskError:
            self._remove_path(staged)
            raise
        self._discard_path(source)
        return destination

    def _rename_into_place(self, source: Path, destination: Path) -> None:
        """Rename source to destination, keeping any existing destination.

        The existing destination is renamed aside and only removed once the source
        has been renamed into its place, and restored if that rename fails, so that
        a failure cannot leave the destination missing. Renaming is atomic, so the
        source is either where it was or stored, and never part-way between.

        Parameters
        ----------
        source: Path
            File or folder to rename. Must be on the same filesystem as the
            destination.
        destination: Path
            Path to rename the source to.

        Raises
        ------
        TransientTaskError
            If the source could not be renamed to the destination.
        """
        stale = None
        try:
            if self._file_operations.exists(destination):
                aside = destination.with_name(f"{destination.name}.{uuid4()}.stale")
                self._file_operations.rename(destination, aside)
                stale = aside
            self._file_operations.rename(source, destination)
        except OSError as exception:
            if stale is not None:
                try:
                    self._file_operations.rename(stale, destination)
                except OSError:
                    self._logger.warning(
                        f"Failed to restore {stale} to {destination}.", exc_info=True
                    )
            raise TransientTaskError(
                f"Failed to store {source} to {destination}"
            ) from exception
        if stale is not None:
            self._remove_path(stale)

    def _make_folder(self, path: Path) -> None:
        """Create folder, and any missing parents of it.

        Parameters
        ----------
        path: Path
            Folder to create.

        Raises
        ------
        TransientTaskError
            If the folder could not be created.
        """
        try:
            self._file_operations.make_folder(path)
        except OSError as exception:
            raise TransientTaskError(f"Failed to create folder {path}") from exception

    def _discard_path(self, path: Path) -> None:
        """Remove file or folder, renaming it before removing it.

        Removing a folder is not atomic, so it is renamed first to keep a failure
        part-way through from leaving a partially removed folder in its place.

        Parameters
        ----------
        path: Path
            File or folder to remove.
        """
        discarded = path.with_name(f"{path.name}.{uuid4()}.discarded")
        try:
            self._file_operations.rename(path, discarded)
        except OSError:
            self._logger.warning(f"Failed to discard {path}.", exc_info=True)
            return
        self._remove_path(discarded)

    def cleanup_processing_task(self, project: Project, task_id: str) -> None:
        """Remove the processing directory for a specific task."""
        task_dir = self._task_processing(project, task_id)
        self._remove_path(task_dir)

    def cleanup_processing_for_project(self, project: Project) -> None:
        """Remove the entire processing directory for a project."""
        proc = self._project_processing(project)
        self._remove_path(proc)

    def _project_processing(self, project: Project) -> Path:
        return self._config.processing.joinpath(project.name + "." + str(project.uid))

    def _task_processing(self, project: Project, task_id: str) -> Path:
        return self._project_processing(project).joinpath(task_id)

    def _task_processing_images(self, project: Project, task_id: str) -> Path:
        path = self._task_processing(project, task_id).joinpath(self._config.image_path)
        self._make_folder(path)
        return path

    def _task_processing_thumbnails(self, project: Project, task_id: str) -> Path:
        path = self._task_processing(project, task_id).joinpath(
            self._config.thumbnail_path
        )
        self._make_folder(path)
        return path

    def _project_thumbnail_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._config.thumbnail_path)
        self._make_folder(path)
        return path

    def _project_images_outbox(self, project: Project, dataset: Dataset) -> Path:
        path = self.project_bundle(project, dataset).joinpath(self._config.image_path)
        self._make_folder(path)
        return path

    def _project_metadata_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._config.metadata_path)
        self._make_folder(path)
        return path

    def _project_pseudonym_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._config.psuedonym_path)
        self._make_folder(path)
        return path

    def _remove_path(self, path: Path):
        """Remove file or folder, logging instead of raising on failure.

        Parameters
        ----------
        path: Path
            File or folder to remove.
        """
        if not self._file_operations.exists(path):
            return
        try:
            self._file_operations.remove(path)
        except OSError:
            self._logger.error(f"Failed to remove {path}", exc_info=True)

    def _copy_folder(self, folder: Path, target_folder: Path, new_name: str) -> Path:
        """Copy folder into target folder under a new name.

        Parameters
        ----------
        folder: Path
            Folder to copy.
        target_folder: Path
            Folder to copy the folder into.
        new_name: str
            Name to copy the folder to.

        Raises
        ------
        TransientTaskError
            If the folder could not be copied.
        """
        copied_path = target_folder.joinpath(new_name)
        self._make_folder(copied_path.parent)
        try:
            self._file_operations.copy(folder, copied_path)
        except OSError as exception:
            raise TransientTaskError(
                f"Failed to copy folder {folder} to {copied_path}"
            ) from exception
        return copied_path
