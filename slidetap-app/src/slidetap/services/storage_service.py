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
import shutil
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from PIL import Image as PILImage

from slidetap.config import StorageConfig
from slidetap.model import Image, Project


class StorageService:
    """Class for storing images and metadata to outbox folder."""

    def __init__(self, config: StorageConfig):
        """Create a storage for storing images and metadata.

        Parameters
        ----------
        outbox: Union[str, Path]
            Path to outbox.
        settings: Optional[StorageSettings] = None
            Settings for storage.

        """
        self._config = config
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
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        self._logger.info(f"Storing thumbnail for {image.uid} to {thumbnail_path}.")
        with open(thumbnail_path, "wb") as thumbnail_file:
            thumbnail_file.write(thumbnail)
        return thumbnail_path

    def get_thumbnail(self, image: Image, size: Tuple[int, int]) -> Optional[bytes]:
        """Return thumbnail for image.

        Parameters
        ----------
        image: Image
            Image to get thumbnail for.
        size: Tuple[int, int]
            Size of thumbnail.

        Returns
        ----------
        Optional[bytes]
            Created thumbnail.
        """
        if image.thumbnail_path is None or not Path(image.thumbnail_path).exists():
            return None
        with PILImage.open(image.thumbnail_path) as thumbnail:
            thumbnail.thumbnail(size)
            with BytesIO() as output:
                thumbnail.save(output, format="PNG")
                return output.getvalue()

    def store(
        self, project: Project, data: Dict[Union[str, Path], Union[StringIO, BytesIO]]
    ):
        """Store data in project's outbox folder.

        Parameters
        ----------
        project: Project
            Project to store data for.
        data: Dict[Union[str, Path], Union[StringIO, BytesIO]]
            Data to store.
        """
        outbox = self.project_outbox(project)
        for path, stream in data.items():
            full_path = outbox.joinpath(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"Storing {path} to {full_path}.")
            if isinstance(stream, StringIO):
                with open(full_path, "w") as file:
                    stream.seek(0)
                    shutil.copyfileobj(stream, file)
            else:
                with open(full_path, "wb") as file:
                    stream.seek(0)
                    shutil.copyfileobj(stream, file)

    def store_metadata(
        self, project: Project, metadata: Dict[Union[str, Path], StringIO]
    ):
        """Store metadata in project's metadata folder

        Parameters
        ----------
        project: Project
            Project to store metadata for.
        metadata: Dict[Union[str, Path], TextIOWrapper]
            Metadata to store.
        """
        metadata_folder = self._project_metadata_outbox(project)
        for path, stream in metadata.items():
            full_path = metadata_folder.joinpath(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"Storing metadata to {full_path}.")
            with open(full_path, "w") as metadata_file:
                stream.seek(0)
                shutil.copyfileobj(stream, metadata_file)

    def store_image(
        self, project: Project, image: Image, path: Path, use_pseudonyms: bool = False
    ) -> Path:
        """Move image to projects's image folder."""
        project_folder = self._project_images_outbox(project)
        if use_pseudonyms:
            if image.pseudonym is None:
                raise ValueError("Image does not have a pseudonym.")
            folder_name = image.pseudonym
        else:
            folder_name = image.identifier
        self._logger.info(
            f"Storing image {image.identifier} to {project_folder.joinpath(folder_name)}."
        )
        return self._move_folder(path, project_folder, True, folder_name)

    def store_download_image(self, project: Project, image: Image, path: Path):
        """Move image to projects's image folder."""
        project_folder = self._config.download.joinpath(project.name, image.identifier)
        folder_name = image.identifier
        self._logger.info(
            f"Storing image {image.identifier} to {project_folder.joinpath(folder_name)}."
        )
        return self._move_folder(path, project_folder, False, folder_name)

    def create_download_image_path(self, project: Project, image: Image) -> Path:
        """Get image storage path for download."""
        project_folder = self._project_download(project)
        folder = project_folder.joinpath(image.identifier)
        self._logger.info(f"Creating image download path {folder}.")
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def cleanup_download_image_path(self, project: Project, image: Image):
        """Cleanup image storage path for download."""
        project_folder = self._project_download(project)
        folder = project_folder.joinpath(image.identifier)
        if folder.exists():
            try:
                shutil.rmtree(folder)
            except Exception:
                self._logger.error(f"Failed to remove folder {folder}", exc_info=True)

    def store_pseudonyms(self, project: Project, pseudonyms: Dict[str, Dict[str, Any]]):
        """Store pseudonyms for project."""
        pseudonym_folder = self._project_pseudonym_outbox(project)
        pseudonym_path = pseudonym_folder.joinpath("pseudonyms.json")
        pseudonym_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pseudonym_path, "w") as pseudonym_file:
            json.dump(pseudonyms, pseudonym_file, indent=4)

    def cleanup_project(self, project: Project):
        """Remove project folder."""
        project_folder = self.project_outbox(project)
        self._remove_folder(project_folder)
        download_folder = self._project_download(project)
        self._remove_folder(download_folder)

    def cleanup_metadata(self, project: Project):
        """Remove metadata for project."""
        metadata_folder = self._project_metadata_outbox(project)
        self._remove_folder(metadata_folder)

    def cleanup_pseudonyms(self, project: Project):
        """Remove pseudonyms for project."""
        pseudonym_folder = self._project_pseudonym_outbox(project)
        self._remove_folder(pseudonym_folder)

    def project_outbox(self, project: Project) -> Path:
        return self.outbox.joinpath(project.name + "." + str(project.uid))

    def _project_download(self, project: Project) -> Path:
        return self._config.download.joinpath(project.name + "." + str(project.uid))

    def _project_thumbnail_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._config.thumbnail_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _project_images_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._config.image_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _project_metadata_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._config.metadata_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _project_pseudonym_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._config.psuedonym_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _remove_folder(self, folder: Path):
        """Remove folder.

        Parameters
        ----------
        folder: Path
            Folder to remove.
        """
        if not folder.exists():
            return
        try:
            shutil.rmtree(folder)
        except Exception:
            self._logger.error(f"Failed to remove folder {folder}", exc_info=True)

    def _move_folder(
        self,
        folder: Path,
        target_folder: Path,
        copy: bool,
        new_name: str,
    ) -> Path:
        """Move or copy folder to project folder.

        Parameters
        ----------
        folder: Path
            Slide folder to move.
        target_folder: Path
            Folder to move the slide folder into.
        copy: bool
            If to copy (True) or move (False).
        random_filename: bool
            If to randomize the filenames.
        """
        image_path = target_folder.joinpath(new_name)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        if copy:
            function = shutil.copytree
        else:
            function = shutil.move
        try:
            function(str(folder), str(image_path))
        except Exception as exception:
            self._logger.error(f"Failed to move folder {folder} due to {exception}.")
        return image_path
