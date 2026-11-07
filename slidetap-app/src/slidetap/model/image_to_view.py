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

"""What viewing an image reads of it."""

from uuid import UUID

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.image_status import PROCESSED_STATUSES, ImageStatus
from slidetap.model.item import ImageFormat


class ImageToView(FrozenBaseModel):
    """An image as viewing it reads it: where it is and what it is, without its
    attributes and relations, as it is read for every tile."""

    uid: UUID
    status: ImageStatus
    format: ImageFormat
    folder_path: str | None = None
    """The folder of its files, or None if it is not downloaded."""
    thumbnail_path: str | None = None
    """The thumbnail made when it was post-processed, if it was."""
    external_identifier: str | None = None
    """What it is known by where it is imported from."""
    filenames: tuple[str, ...] = ()
    """Its files, relative to its folder."""

    @property
    def processed(self) -> bool:
        """Whether its folder holds post-processed image data."""
        return self.status in PROCESSED_STATUSES
