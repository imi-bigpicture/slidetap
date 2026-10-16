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
from collections.abc import Iterable
from pathlib import Path

from slidetap.external_interfaces import (
    ImageImportInterface,
)
from slidetap.model import Image
from slidetap.model.project import Project
from slidetap_example.config import ExampleConfig


class ExampleImageImportInterface(ImageImportInterface):
    def __init__(self, config: ExampleConfig):
        self._image_folder = config.example_test_data_path
        self._image_extension = config.example_test_data_image_extension
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def download(self, image: Image, project: Project) -> tuple[Path, Iterable[Path]]:
        """Find the image file in the test data folder.

        The file is ``<identifier>/<identifier><extension>`` in the test data
        folder. The extension is appended rather than replacing a suffix, so an
        identifier with a dot, such as ``A.1``, keeps all of its name.

        Raises
        ------
        ValueError
            If the identifier is not a single folder name, so that the file
            would be looked for outside the test data folder.
        FileNotFoundError
            If there is no such file.
        """
        image_folder = self._image_folder.joinpath(image.identifier)
        test_data_folder = self._image_folder.resolve()
        if (
            Path(image.identifier).name != image.identifier
            or image.identifier in ("", ".", "..")
            or image_folder.resolve().parent != test_data_folder
        ):
            raise ValueError(
                f"Image identifier {image.identifier!r} is not a folder name in "
                "the test data folder."
            )
        image_path = image_folder.joinpath(f"{image.identifier}{self._image_extension}")
        self._logger.debug(f"Image path: {image_path}")
        if not image_path.exists():
            raise FileNotFoundError(
                f"Image path {image_path} did not exist. Image {image.name} failed."
            )

        self._logger.debug(f"Downloading image {image.name}.")
        return image_folder, [image_path]
