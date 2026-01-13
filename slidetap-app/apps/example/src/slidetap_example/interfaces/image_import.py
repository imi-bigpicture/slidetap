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

import logging
from pathlib import Path
from typing import Iterable, Tuple

from slidetap.external_interfaces import (
    ImageImportInterface,
)
from slidetap.model.item import Image
from slidetap.model.project import Project

from slidetap_example.config import ExampleConfig


class ExampleImageImportInterface(ImageImportInterface):
    def __init__(self, config: ExampleConfig):
        self._image_folder = config.example_test_data_path
        self._image_extension = config.example_test_data_image_extension
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def download(self, image: Image, project: Project) -> Tuple[Path, Iterable[Path]]:
        image_folder = self._image_folder.joinpath(image.identifier)
        image_path = image_folder.joinpath(image.identifier).with_suffix(
            self._image_extension
        )
        self._logger.debug(f"Image path: {image_path}")
        if not image_path.exists():
            raise FileNotFoundError(
                f"Image path {image_path} did not exist. Image {image.name} failed."
            )

        self._logger.debug(f"Downloading image {image.name}.")
        return image_folder, [image_path]
