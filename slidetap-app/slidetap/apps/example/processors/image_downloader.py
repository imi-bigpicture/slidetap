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

import logging
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

from slidetap.config import Config
from slidetap.database import DatabaseImage, DatabaseImageFile
from slidetap.model.schema.root_schema import RootSchema
from slidetap.task.processors.image.image_downloader import ImageDownloader
from sqlalchemy.orm import Session


class ExampleImageDownloader(ImageDownloader):
    def __init__(
        self,
        root_schema: RootSchema,
        image_folder: Path,
        image_extension: str,
        config: Config,
    ):
        self._image_folder = image_folder
        self._image_extension = image_extension
        super().__init__(root_schema, config)

    def run(self, image_uid: UUID, **kwargs: Dict[str, Any]):
        with self._database_service.get_session() as session:
            image = self._database_service.get_image(session, image_uid)
            self._download_image(image, session)

    def _download_image(self, image: DatabaseImage, session: Session):
        image_folder = self._image_folder.joinpath(image.identifier)
        image_path = image_folder.joinpath(image.identifier).with_suffix(
            self._image_extension
        )
        logging.debug(f"Image path: {image_path}")
        if image_path.exists():
            image.set_as_downloading()
            logging.debug(f"Downloading image {image.name}.")
            image.folder_path = str(image_folder)
            image.files = [DatabaseImageFile(image_path.name)]
            image.set_as_downloaded()
        else:
            logging.error(
                f"Failing image {image.name}. Image path {image_path} did not exist."
            )
            image.set_as_downloading_failed()
            self._item_service.select_image(image, False, session=session)
