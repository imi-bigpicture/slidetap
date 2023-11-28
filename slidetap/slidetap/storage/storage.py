"""Storing images and metadata to outbox."""
import json
import os
import shutil
from io import StringIO, BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from PIL import Image as PILImage
from flask import current_app

from slidetap.database.project import Image, Project
from slidetap.flask_extension import FlaskExtension


class Storage(FlaskExtension):
    """Class for storing images and metadata to outbox folder."""

    def __init__(self, outbox: Union[str, Path]):
        """Create a storage for storing images and metadata.

        Parameters
        ----------
        outbox: Union[str, Path]
            Path to outbox.

        """
        if isinstance(outbox, str):
            outbox = Path(outbox)
        self._outbox = outbox

    def store_thumbnail(
        self, image: Image, thumbnail: bytes, uid_name: bool = False
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
        if uid_name:
            name = str(image.uid)
        else:
            name = image.name
        thumbnail_path = thumbnails_folder.joinpath(name + ".jpeg")
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

    def store_metadata(self, project: Project, metadata: Dict[str, StringIO]):
        """Store metadata in project's metadata folder

        Parameters
        ----------
        project: Project
            Project to store metadata for.
        metadata: Dict[str, TextIOWrapper]
            Metadata to store.
        """
        metadata_folder = self.project_metadata_outbox(project)
        for path, data in metadata.items():
            with open(metadata_folder.joinpath(path), "w") as metadata_file:
                data.seek(0)
                shutil.copyfileobj(data, metadata_file)

    def store_image(self, image: Image, path: Path, uid_folders: bool = False) -> Path:
        """Move image to projects's image folder."""
        project_folder = self.project_images_outbox(image.project)
        if uid_folders:
            folder_name = str(image.uid)
        else:
            folder_name = image.name
        return self._move_folder(path, project_folder, True, folder_name)

    def store_pseudonyms(self, project: Project, pseudonyms: Dict[str, Dict[str, Any]]):
        """Store pseudonyms for project."""
        pseudonym_folder = self.project_pseudonym_outbox(project)
        pseudonym_path = pseudonym_folder.joinpath("pseudonyms.json")
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
        path = self.project_outbox(project).joinpath("thumbnails")
        os.makedirs(path, exist_ok=True)
        return path

    def project_images_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath("images")
        os.makedirs(path, exist_ok=True)
        return path

    def project_metadata_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath("metadata")
        os.makedirs(path, exist_ok=True)
        return path

    def project_pseudonym_outbox(self, project: Project) -> Path:
        path = self.project_outbox(project).joinpath("pseudonyms")
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
