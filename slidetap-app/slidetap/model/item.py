import dataclasses
from dataclasses import dataclass
from typing import Dict, List, Optional, TypeVar
from uuid import UUID

from slidetap.model.attribute import Attribute
from slidetap.model.image_status import ImageStatus

ItemType = TypeVar("ItemType", bound="Item")


@dataclass
class Item:
    uid: UUID
    identifier: str
    dataset_uid: UUID
    schema_uid: UUID
    batch_uid: Optional[UUID] = None
    name: Optional[str] = None
    pseudonym: Optional[str] = None
    selected: bool = True
    valid: Optional[bool] = None
    valid_attributes: Optional[bool] = None
    valid_relations: Optional[bool] = None
    attributes: Dict[str, Attribute] = dataclasses.field(default_factory=dict)


@dataclass
class Observation(Item):
    sample: Optional[UUID] = None
    image: Optional[UUID] = None
    annotation: Optional[UUID] = None


@dataclass
class Annotation(Item):
    image: Optional[UUID] = None
    obseration: List[UUID] = dataclasses.field(default_factory=list)


@dataclass
class ImageFile:
    uid: UUID
    filename: str


@dataclass
class Image(Item):
    status: ImageStatus = ImageStatus.NOT_STARTED
    external_identifier: Optional[str] = None
    folder_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status_message: Optional[str] = None
    files: List[ImageFile] = dataclasses.field(default_factory=list)
    samples: List[UUID] = dataclasses.field(default_factory=list)
    annotations: List[UUID] = dataclasses.field(default_factory=list)
    observations: List[UUID] = dataclasses.field(default_factory=list)


@dataclass
class Sample(Item):
    parents: List[UUID] = dataclasses.field(default_factory=list)
    children: List[UUID] = dataclasses.field(default_factory=list)
    images: List[UUID] = dataclasses.field(default_factory=list)
    observations: List[UUID] = dataclasses.field(default_factory=list)
