#    Copyright 2026 SECTRA AB
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

"""Viewing a whole slide image (WSI), as tiles at Deep Zoom levels."""

from abc import ABCMeta, abstractmethod

from slidetap.model import Dzi, ImageToView


class ImageViewInterface(metaclass=ABCMeta):
    """Reads a whole slide image for the client to view: its Deep Zoom
    description, its tiles and its thumbnail.

    :py:class:`FileImageViewInterface` reads an image from its downloaded
    files. An application that views images before they are downloaded, as
    where they are not pre-processed separately, reads those from where they
    are imported from, and hands the downloaded ones to it.
    """

    @abstractmethod
    def get_dzi(self, image: ImageToView, base_url: str) -> Dzi:
        """The Deep Zoom description of the image.

        Parameters
        ----------
        image: ImageToView
            The image to describe.
        base_url: str
            The url the tiles of the image are requested from, to put in the
            description.

        Raises
        ------
        ValueError
            If the image cannot be read.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_tile(
        self,
        image: ImageToView,
        dzi_level: int,
        x: int,
        y: int,
        extension: str,
        z: int | None = None,
    ) -> bytes:
        """A JPEG encoded tile of the image, at a Deep Zoom level, where level 0
        is the image scaled down to a single pixel.

        Parameters
        ----------
        image: ImageToView
            The image to read.
        dzi_level: int
            The Deep Zoom level of the tile.
        x: int
            The column of the tile.
        y: int
            The row of the tile.
        extension: str
            The extension the tile was requested with.
        z: int | None = None
            The focal plane, by its position among the planes of the
            description, or None for the default plane.

        Raises
        ------
        ValueError
            If the image cannot be read, or the tile is outside it.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_thumbnail(
        self, image: ImageToView, width: int, height: int, format: str
    ) -> bytes | None:
        """A thumbnail of the image within the given size, encoded in the given
        format, or None if the image has none to give."""
        raise NotImplementedError()
