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
from collections.abc import Iterable
from pathlib import Path

from slidetap.model import Image, Project


class ImageImportInterface(metaclass=ABCMeta):
    """
    Metaclass for interface for importing images. Implementations must implement:
    - download: Download image file into download storage.

    Implementations may override:
    - pre_processes_separately: False if the images are pre-processed as
      they are post-processed.
    """

    @property
    def pre_processes_separately(self) -> bool:
        """Whether the images of a batch are pre-processed in a step of their
        own: a batch is curated as searched, its images then
        downloaded and their metadata imported, and the batch curated again
        before it is post-processed.

        False for an import whose images curation views where they are imported
        from, needing nothing from their files: a batch then goes from the
        curation of the search straight to post-processing, and each image is
        downloaded and its metadata imported in the same task, right before it
        is converted. The :py:class:`ApplicationPolicy` of the application follows
        from it.
        """
        return True

    @abstractmethod
    def download(self, image: Image, project: Project) -> tuple[Path, Iterable[Path]]:
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
        tuple[Path, Iterable[Path]]
            The path to the image folder and a list of paths to the downloaded images.
        """

        raise NotImplementedError()
