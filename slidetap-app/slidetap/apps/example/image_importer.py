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

"""Image importer that provides images stored in folder."""

from pathlib import Path
from typing import Optional

from flask import Flask, current_app
from slidetap.database.project import Image, ImageFile, Project
from slidetap.database.schema import ImageSchema
from slidetap.importer.image import ImageImporter
from slidetap.model import Session
from slidetap.tasks.scheduler import Scheduler


class ExampleImageImporter(ImageImporter):
    def __init__(
        self,
        scheduler: Scheduler,
        image_folder: Path,
        image_extension: str,
        app: Optional[Flask] = None,
    ):
        self._image_folder = image_folder
        self._image_extension = image_extension
        super().__init__(scheduler, app)

    def pre_process(self, session: Session, project: Project):
        image_schema = ImageSchema.get(project.root_schema, "wsi")
        images = Image.get_for_project(project.uid, image_schema.uid, selected=True)
        for image in images:
            self._download_image(image)
            if image.downloaded and image.selected:
                self._pre_process_image(image)

    def redo_image_download(self, session: Session, image: Image):
        image.reset_as_not_started()
        self._download_image(image)

    def redo_image_pre_processing(self, image: Image):
        image.reset_as_downloaded()
        self._pre_process_image(image)

    def _download_image(self, image: Image):
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

        else:
            current_app.logger.error(
                f"Failing image {image.name}. Image path {image_path} did not exist."
            )
            image.set_as_downloading_failed()
            image.select(False)

    def _pre_process_image(self, image: Image):
        current_app.logger.debug(f"Pre-processing image {image.name}.")
        self._scheduler.pre_process_image(image)
