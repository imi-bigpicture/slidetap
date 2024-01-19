"""Image importer that provides images stored in folder."""
from pathlib import Path
from typing import Optional

from flask import Flask, current_app

from slidetap.database.project import Image, ImageFile, Project
from slidetap.database.schema import ImageSchema
from slidetap.image_processing import ImageProcessor
from slidetap.importer.image.image_importer import ImageImporter
from slidetap.model import Session


class ExampleImageImporter(ImageImporter):
    def __init__(
        self,
        pre_processor: ImageProcessor,
        image_folder: Path,
        image_extension: str,
        app: Optional[Flask] = None,
    ):
        super().__init__(app)
        self._pre_processor = pre_processor
        self._image_folder = image_folder
        self._image_extension = image_extension

    def init_app(self, app: Flask):
        super().init_app(app)
        self._pre_processor.init_app(app)

    def download(self, session: Session, project: Project):
        image_schema = ImageSchema.get(project.schema, "wsi")
        images = Image.get_for_project(project.uid, image_schema.uid, True)
        for image in images:
            image_folder = self._image_folder.joinpath(image.identifier)
            image_path = image_folder.joinpath(image.identifier).with_suffix(
                self._image_extension
            )
            current_app.logger.debug(f"Image path: {image_path}")
            if image_path.exists():
                image.set_as_downloading()
                current_app.logger.debug(f"Downloading image {image.name}.")
                image.set_folder_path(image_folder)
                image.set_files([ImageFile(image_path.name)])
                image.set_as_downloaded()
                self._pre_processor.add_job(image.uid)
            else:
                current_app.logger.debug(
                    f"Failing image {image.name}. Image path {image_path} did not exist."
                )
                image.set_as_failed()
