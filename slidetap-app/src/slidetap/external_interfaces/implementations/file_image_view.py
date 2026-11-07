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

"""Viewing an image from its downloaded files."""

import io
from pathlib import Path

from PIL import Image as PILImage
from wsidicom import WsiDicom
from wsidicomizer import WsiDicomizer

from slidetap.external_interfaces.image_view import ImageViewInterface
from slidetap.model import Dzi, ImageToView
from slidetap.services.image_service import ImageCache


class FileImageViewInterface(ImageViewInterface):
    """Reads an image from its downloaded files.

    An image not downloaded has nothing to read here: an application that views
    images before they are downloaded reads them from where they are imported
    from, and hands the downloaded ones to this.
    """

    def __init__(self, image_cache: ImageCache):
        self._image_cache = image_cache

    def get_dzi(self, image: ImageToView, base_url: str) -> Dzi:
        with self._image_cache.get(image) as wsi:
            if wsi is None:
                raise ValueError(f"Image {image.uid} is not downloaded.")
            return Dzi(
                url=base_url,
                width=wsi.size.width,
                height=wsi.size.height,
                tile_size=wsi.tile_size.width,
                tile_format="jpeg",
                planes=wsi.pyramids[0].base_level.focal_planes,
                channels=wsi.pyramids[0].base_level.optical_paths,
            )

    def get_tile(
        self,
        image: ImageToView,
        dzi_level: int,
        x: int,
        y: int,
        extension: str,
        z: int | None = None,
    ) -> bytes:
        with self._image_cache.get(image) as wsi:
            if wsi is None:
                raise ValueError(f"Image {image.uid} is not downloaded.")
            level = wsi.pyramids[0].highest_level - dzi_level
            return wsi.read_encoded_tile(level, (x, y), z)

    def get_thumbnail(
        self, image: ImageToView, width: int, height: int, format: str
    ) -> bytes | None:
        """Read from the thumbnail made when the image was post-processed, and
        otherwise made from the image files for this request alone. A thumbnail
        made here is not stored: the outbox is handed over as it is, and a
        thumbnail named after the image is not something to hand over with a
        pseudonymised project.
        """
        if image.folder_path is None:
            return None
        if image.thumbnail_path is None:
            return self._create_thumbnail(image, width, height, format)
        return self._read_thumbnail(image, width, height, format)

    def _read_thumbnail(
        self, image: ImageToView, width: int, height: int, format: str
    ) -> bytes | None:
        """Read the thumbnail stored for an image, scaled to the given size."""
        if image.thumbnail_path is None or not Path(image.thumbnail_path).exists():
            return None
        with PILImage.open(image.thumbnail_path) as thumbnail:
            thumbnail.thumbnail((width, height))
            with io.BytesIO() as output:
                thumbnail.save(output, format)
                return output.getvalue()

    def _create_thumbnail(
        self, image: ImageToView, width: int, height: int, format: str
    ):
        if image.folder_path is None:
            raise ValueError(f"Image {image.uid} is not downloaded.")
        if image.processed:
            with WsiDicom.open(image.folder_path) as wsi:
                thumbnail = wsi.read_thumbnail((width, height))

        else:
            if not image.filenames:
                raise ValueError(f"Image {image.uid} has no files.")
            with WsiDicomizer.open(
                Path(image.folder_path).joinpath(image.filenames[0])
            ) as wsi:
                thumbnail = wsi.read_thumbnail((width, height))
        with io.BytesIO() as output:
            thumbnail.save(output, format)
            return output.getvalue()
