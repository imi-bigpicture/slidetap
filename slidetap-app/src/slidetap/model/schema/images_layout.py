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

"""Images layout model for reading what was scanned under an item."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.schema.attribute_value_layout import AttributeValueLayout


class ImageOrder(StrEnum):
    """What the images of a group are put in order by."""

    IDENTIFIER = "identifier"
    NAME = "name"


class ImageAttributeLayout(AttributeValueLayout):
    """An attribute to show with an image, and where to read it from."""

    schema_uid: UUID | None = None
    """Whose attribute this is.

    The image's own when not given. Otherwise the nearest item of that kind
    above it — the stain is recorded on the slide a whole slide image was
    scanned from, not on the image.
    """


class ImagesLayout(FrozenBaseModel):
    """What was scanned under one kind of item, as pictures.

    Named attributes rather than whatever an image carries: a thumbnail has
    room for an identifier and a word or two beside it.
    """

    uid: UUID
    name: str
    display_name: str

    schema_uid: UUID
    """Schema of the item the images are shown for."""

    group_by_schema_uid: UUID
    """What to gather the images under — the schema of the item each group
    stands for, which may be the item itself."""

    group_name_schema_uids: list[UUID] = Field(default_factory=list)
    """What names a group, in the order given.

    The item of each kind at or above the group, by its name where it has one.
    A block is called "A" and only its identifier says which specimen it was
    cut from, so a gallery of blocks names them by both. The group's own
    identifier when not given.
    """

    group_attributes: list[AttributeValueLayout] = Field(default_factory=list)
    """What to show on a group beside its name, in the order given."""

    image_schema_uids: list[UUID] = Field(default_factory=list)
    """Which images to show. All of them when not given."""

    image_attributes: list[ImageAttributeLayout] = Field(default_factory=list)
    """What to show on an image beside its identifier, in the order given."""

    image_order: ImageOrder = ImageOrder.IDENTIFIER
    """What the images of a group are put in order by.

    By name where the pictures of a group are told apart by one — several
    scans of the same slide, say. Never in pseudonym mode, where only the
    pseudonym is to be shown.
    """
