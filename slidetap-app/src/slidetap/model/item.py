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

from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import (
    Annotated,
    Any,
    Literal,
    TypeVar,
)
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.image_status import ImageStatus
from slidetap.model.item_value_type import ItemValueType
from slidetap.model.review_status import ReviewStatus

ItemType = TypeVar("ItemType", bound="Item")


class Item(CamelCaseBaseModel):
    uid: UUID
    identifier: str
    dataset_uid: UUID
    schema_uid: UUID
    batch_uid: UUID | None = None
    name: str | None = None
    external_identifier: str | None = None
    pseudonym: str | None = None
    selected: bool = True
    valid: bool | None = None
    valid_attributes: bool | None = None
    valid_relations: bool | None = None
    valid_pseudonym: bool | None = None
    attributes: dict[str, AnyAttribute] = Field(default_factory=dict)
    private_attributes: dict[str, AnyAttribute] = Field(default_factory=dict)
    tags: list[UUID] = Field(default_factory=list)
    comment: str | None = None
    review_status: ReviewStatus = ReviewStatus.NOT_REVIEWED
    review_reason: str | None = None
    """Why review was asked for — set by whatever flagged the item, and left
    alone once it is reviewed so the reason it was raised stays readable."""
    last_saved: datetime | None = None
    """When a user last saved this item, so the one worked on last can be found
    again. Empty for an item nobody has edited: an import is not a save."""


class Observation(Item):
    sample: tuple[UUID, UUID] | None = None
    image: tuple[UUID, UUID] | None = None
    annotation: tuple[UUID, UUID] | None = None
    item_value_type: Literal[ItemValueType.OBSERVATION] = ItemValueType.OBSERVATION


class Annotation(Item):
    image: tuple[UUID, UUID] | None = None
    observation: dict[UUID, list[UUID]] = Field(default=defaultdict(list))
    item_value_type: Literal[ItemValueType.ANNOTATION] = ItemValueType.ANNOTATION


class ImageFile(CamelCaseBaseModel):
    uid: UUID
    filename: str


class ImageFormat(Enum):
    DICOM_WSI = "DICOM_WSI"
    OTHER_WSI = "OTHER_WSI"
    DICOM_SINGLE_FRAME = "DICOM_SINGLE_FRAME"
    OTHER_SINGLE_FRAME = "OTHER_SINGLE_FRAME"


class Image(Item):
    status: ImageStatus = ImageStatus.NOT_STARTED
    folder_path: str | None = Field(default=None, exclude=True)
    thumbnail_path: str | None = Field(default=None, exclude=True)
    status_message: str | None = None
    files: list[ImageFile] = Field(default_factory=list)
    samples: dict[UUID, list[UUID]] = Field(default=defaultdict(list))
    annotations: dict[UUID, list[UUID]] = Field(default=defaultdict(list))
    observations: dict[UUID, list[UUID]] = Field(default=defaultdict(list))
    format: ImageFormat
    item_value_type: Literal[ItemValueType.IMAGE] = ItemValueType.IMAGE


class Sample(Item):
    parents: dict[UUID, list[UUID]] = Field(default=defaultdict(list))
    children: dict[UUID, list[UUID]] = Field(default=defaultdict(list))
    images: dict[UUID, list[UUID]] = Field(default=defaultdict(list))
    observations: dict[UUID, list[UUID]] = Field(default=defaultdict(list))
    item_value_type: Literal[ItemValueType.SAMPLE] = ItemValueType.SAMPLE


class GroupedImage(CamelCaseBaseModel):
    """An image as a gallery shows it: the image, and what to say beside it."""

    image: Image

    attributes: dict[str, AnyAttribute] = Field(default_factory=dict)
    """What the layout asked for, in the order it asked. Read from the image
    or from the item above it the layout named — the stain is recorded on the
    slide rather than on the picture of it."""


class ImageGroup(CamelCaseBaseModel):
    identifier: str
    name: str | None
    schema_uid: UUID

    label: str
    """What to call the group, as the layout names it — the specimen and the
    block, where a block alone is called "A". Always set: it falls back to the
    identifier, so there is nothing for a reader of this to decide."""

    images: list[GroupedImage]

    attributes: dict[str, AnyAttribute] = Field(default_factory=dict)
    """What the layout asked for of the item the group stands for."""


AnyItem = Annotated[
    Sample | Image | Annotation | Observation,
    Field(discriminator="item_value_type"),
]


def item_factory(data: dict[str, Any]) -> AnyItem:
    item_value_type = ItemValueType(data.pop("itemValueType"))
    if item_value_type == ItemValueType.OBSERVATION:
        return Observation.model_validate(data)
    if item_value_type == ItemValueType.ANNOTATION:
        return Annotation.model_validate(data)
    if item_value_type == ItemValueType.IMAGE:
        return Image.model_validate(data)
    if item_value_type == ItemValueType.SAMPLE:
        return Sample.model_validate(data)
    raise ValueError(
        f"Unknown item item_value_type: {data.get('item_value_type')}"
    ) from None


class ReviewRequest(CamelCaseBaseModel):
    """Move an item to a review status. ``reason`` is written only when the
    status is ``FLAGGED``."""

    status: ReviewStatus
    reason: str | None = None


class ReviewQueueItem(CamelCaseBaseModel):
    """One entry in the list a reviewer works through.

    Carries the status and the reason so the list can say where each entry
    stands and what it was flagged for without reading every item in full.
    """

    uid: UUID
    identifier: str
    pseudonym: str | None = None
    review_status: ReviewStatus = ReviewStatus.NOT_REVIEWED
    review_reason: str | None = None
    last_saved: datetime | None = None


class ItemNeighbours(CamelCaseBaseModel):
    """What comes before and after an item among those of its own kind, so that
    a view of one item can be stepped through."""

    previous_uid: UUID | None = None
    next_uid: UUID | None = None


class NewChildSuggestion(CamelCaseBaseModel):
    """What adding an item of a schema under another item would do.

    The identifier is derived, so it can collide with one already used — most
    often by an item that was taken out of the project. Whoever offers the
    addition needs to know that, since adding under a used name gives back the
    item that has it rather than a new one.
    """

    identifier: str
    existing_uid: UUID | None = None
    """The item already carrying the identifier, where there is one."""

    existing_in_project: bool = False
    """Whether that item is still in the project, or was removed from it."""


class MoveAttributeRequest(CamelCaseBaseModel):
    """Swap an attribute value between two existing items."""

    source_item_uid: UUID
    attribute_tag: str
    target_item_uid: UUID
