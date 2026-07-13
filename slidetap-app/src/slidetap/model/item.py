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


class ImageGroup(CamelCaseBaseModel):
    identifier: str
    name: str | None
    schema_uid: UUID
    images: list[Image]


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


class MoveAttributeRequest(CamelCaseBaseModel):
    """Swap an attribute value between two items.

    Exactly one of ``target_item_uid`` or ``target_parent_uid`` must be set:
    set ``target_item_uid`` to swap with an existing item; set
    ``target_parent_uid`` to create a new child of that parent (with the
    source's schema) and swap with it.
    """

    source_item_uid: UUID
    attribute_tag: str
    target_item_uid: UUID | None = None
    target_parent_uid: UUID | None = None


class MoveAttributeResponse(CamelCaseBaseModel):
    created_item_uid: UUID | None = None
