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

"""Image downloader that provides images stored in folder."""

from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from flask import Flask, current_app
from slidetap.database import DatabaseImage, DatabaseImageFile
from slidetap.model.schema.root_schema import RootSchema
from slidetap.task.processors.image.image_downloader import ImageDownloader


class ExampleImageDownloader(ImageDownloader):
    def __init__(
        self,
        root_schema: RootSchema,
        image_folder: Path,
        image_extension: str,
        app: Optional[Flask] = None,
    ):
        self._image_folder = image_folder
        self._image_extension = image_extension
        super().__init__(root_schema, app)

    def run(self, image_uid: UUID, **kwargs: Dict[str, Any]):
        with self._app.app_context():
            image = DatabaseImage.get(image_uid)
            self._download_image(image)

    def _download_image(self, image: DatabaseImage):
        image_folder = self._image_folder.joinpath(image.identifier)
        image_path = image_folder.joinpath(image.identifier).with_suffix(
            self._image_extension
        )
        current_app.logger.debug(f"Image path: {image_path}")
        if image_path.exists():
            image.set_as_downloading()
            current_app.logger.debug(f"Downloading image {image.name}.")
            image.set_folder_path(image_folder)
            image.set_files([DatabaseImageFile(image_path.name)])
            image.set_as_downloaded()

        else:
            current_app.logger.error(
                f"Failing image {image.name}. Image path {image_path} did not exist."
            )
            image.set_as_downloading_failed()
            self._item_service.select_image(image, False)
