"""Storing images and metadata to outbox."""

import json
import os
import shutil
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from flask import current_app
from PIL import Image as PILImage

from slidetap.database import Image, Project
from slidetap.flask_extension import FlaskExtension


@dataclass
class StorageSettings:
    image_path: str = "images"
    metadata_path: str = "metadata"
    thumbnail_path: str = "thumbnails"
    psuedonym_path: str = "pseudonyms"


class Storage(FlaskExtension):
    """Class for storing images and metadata to outbox folder."""

    def __init__(
        self, outbox: Union[str, Path], settings: Optional[StorageSettings] = None
    ):
        """Create a storage for storing images and metadata.

        Parameters
        ----------
        outbox: Union[str, Path]
            Path to outbox.
        settings: Optional[StorageSettings] = None
            Settings for storage.

        """
        if isinstance(outbox, str):
            outbox = Path(outbox)
        if settings is None:
            settings = StorageSettings()
        self._outbox = outbox
        self._settings = settings

    def store_thumbnail(
        self, image: Image, thumbnail: bytes, use_pseudonyms: bool = False
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
        thumbnails_folder = self.project_thumbnail_outbox(image.project)
        if use_pseudonyms:
            if image.pseudonym is None:
                raise ValueError("Image does not have a pseudonym.")
            name = image.pseudonym
        else:
            name = image.identifier
        thumbnail_path = thumbnails_folder.joinpath(name + ".jpeg")
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
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
        if not Path(image.thumbnail_path).exists():
            return None
        with PILImage.open(image.thumbnail_path) as thumbnail:
            thumbnail.thumbnail(size)
            with BytesIO() as output:
                thumbnail.save(output, format="PNG")
                return output.getvalue()

    def store(self, project, data: Dict[Union[str, Path], Union[StringIO, BytesIO]]):
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
        metadata_folder = self.project_metadata_outbox(project)
        for path, stream in metadata.items():
            full_path = metadata_folder.joinpath(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w") as metadata_file:
                stream.seek(0)
                shutil.copyfileobj(stream, metadata_file)

    def store_image(
        self, image: Image, path: Path, use_pseudonyms: bool = False
    ) -> Path:
        """Move image to projects's image folder."""
        project_folder = self.project_images_outbox(image.project)
        if use_pseudonyms:
            if image.pseudonym is None:
                raise ValueError("Image does not have a pseudonym.")
            folder_name = image.pseudonym
        else:
            folder_name = image.identifier
        return self._move_folder(path, project_folder, True, folder_name)

    def store_pseudonyms(self, project: Project, pseudonyms: Dict[str, Dict[str, Any]]):
        """Store pseudonyms for project."""
        pseudonym_folder = self.project_pseudonym_outbox(project)
        pseudonym_path = pseudonym_folder.joinpath("pseudonyms.json")
        pseudonym_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pseudonym_path, "w") as pseudonym_file:
            json.dump(pseudonyms, pseudonym_file, indent=4)

    def cleanup_metadata(self, project: Project):
        """Remove metadata for project."""
        metadata_folder = self.project_metadata_outbox(project)
        self._remove_folder(metadata_folder)

    def cleanup_pseudonyms(self, project: Project):
        """Remove pseudonyms for project."""
        pseudonym_folder = self.project_pseudonym_outbox(project)
        self._remove_folder(pseudonym_folder)

    def project_outbox(self, project: Project) -> Path:
        return self._outbox.joinpath(project.name + "." + str(project.uid))

    def project_thumbnail_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._settings.thumbnail_path)
        os.makedirs(path, exist_ok=True)
        return path

    def project_images_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._settings.image_path)
        os.makedirs(path, exist_ok=True)
        return path

    def project_metadata_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._settings.metadata_path)
        os.makedirs(path, exist_ok=True)
        return path

    def project_pseudonym_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath(self._settings.psuedonym_path)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def _remove_folder(folder: Path):
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
            current_app.logger.error(f"Failed to remove folder {folder}", exc_info=True)

    @staticmethod
    def _move_folder(
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
            current_app.logger.error(
                f"Failed to move folder {folder} due to {exception}."
            )
        return image_path
