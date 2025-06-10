from typing import Annotated, Any, Dict, List, Literal, Optional, TypeVar, Union
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import Attribute
from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.image_status import ImageStatus
from slidetap.model.item_value_type import ItemValueType

ItemType = TypeVar("ItemType", bound="Item")


class Item(CamelCaseBaseModel):
    uid: UUID
    identifier: str
    dataset_uid: UUID
    schema_uid: UUID
    batch_uid: Optional[UUID] = None
    name: Optional[str] = None
    external_identifier: Optional[str] = None
    pseudonym: Optional[str] = None
    selected: bool = True
    valid: Optional[bool] = None
    valid_attributes: Optional[bool] = None
    valid_relations: Optional[bool] = None
    attributes: Dict[str, Attribute] = Field(default_factory=dict)
    item_value_type: ItemValueType


class Observation(Item):
    sample: Optional[UUID] = None
    image: Optional[UUID] = None
    annotation: Optional[UUID] = None
    item_value_type: Literal[ItemValueType.OBSERVATION] = ItemValueType.OBSERVATION


class Annotation(Item):
    image: Optional[UUID] = None
    obseration: List[UUID] = Field(default_factory=list)
    item_value_type: Literal[ItemValueType.ANNOTATION] = ItemValueType.ANNOTATION


class ImageFile(CamelCaseBaseModel):
    uid: UUID
    filename: str


class Image(Item):
    status: ImageStatus = ImageStatus.NOT_STARTED
    folder_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status_message: Optional[str] = None
    files: List[ImageFile] = Field(default_factory=list)
    samples: List[UUID] = Field(default_factory=list)
    annotations: List[UUID] = Field(default_factory=list)
    observations: List[UUID] = Field(default_factory=list)
    item_value_type: Literal[ItemValueType.IMAGE] = ItemValueType.IMAGE


class Sample(Item):
    parents: List[UUID] = Field(default_factory=list)
    children: List[UUID] = Field(default_factory=list)
    images: List[UUID] = Field(default_factory=list)
    observations: List[UUID] = Field(default_factory=list)
    item_value_type: Literal[ItemValueType.SAMPLE] = ItemValueType.SAMPLE


class ImageGroup(CamelCaseBaseModel):
    identifier: str
    name: Optional[str]
    schema_uid: UUID
    images: List[Image]


AnyItem = Annotated[
    Union[Sample, Image, Annotation, Observation],
    Field(discriminator="item_value_type"),
]


def item_factory(data: Dict[str, Any]) -> AnyItem:
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
