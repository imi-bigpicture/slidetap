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

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Iterable, Tuple

from slidetap.model import Image, Project


class ImageImportInterface(metaclass=ABCMeta):
    """
    Metaclass for interface for importing images. Implementations must implement:
    - download: Download image file into download storage.
    """

    @abstractmethod
    def download(self, image: Image, project: Project) -> Tuple[Path, Iterable[Path]]:
        """
        Download image file to storage download folder.

        Must throw an exception if the image cannot be downloaded.

        Parameters
        ----------
        image: Image
            The image to download.
        project: Project
            The project to download the image for.

        Returns
        -------
        Tuple[Path, Iterable[Path]]
            The path to the image folder and a list of paths to the downloaded images.
        """

        raise NotImplementedError()
