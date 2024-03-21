"""Image importer that provides images stored in folder."""

from pathlib import Path
from typing import Optional

from flask import Flask, current_app

from slidetap.database.project import Image, ImageFile, Project
from slidetap.database.schema import ImageSchema
from slidetap.image_processing.step_image_processor import ImagePreProcessor
from slidetap.importer.image.image_processing_importer import ImageProcessingImporter
from slidetap.model import Session
from slidetap.scheduler import Scheduler


class ExampleImageImporter(ImageProcessingImporter):
    def __init__(
        self,
        scheduler: Scheduler,
        pre_processor: ImagePreProcessor,
        image_folder: Path,
        image_extension: str,
        app: Optional[Flask] = None,
    ):
        self._pre_processor = pre_processor
        self._image_folder = image_folder
        self._image_extension = image_extension
        super().__init__(scheduler, pre_processor, app)

    def init_app(self, app: Flask):
        super().init_app(app)
        self._pre_processor.init_app(app)

    def preprocess(self, session: Session, project: Project):
        image_schema = ImageSchema.get(project.root_schema, "wsi")
        images = Image.get_for_project(project.uid, image_schema.uid, selected=True)
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
                self._scheduler.add_job(
                    str(image.uid),
                    self.processor.run,
                    {"image_uid": image.uid},
                )
            else:
                current_app.logger.debug(
                    f"Failing image {image.name}. Image path {image_path} did not exist."
                )
                image.set_as_downloading_failed()
                image.select(False)
