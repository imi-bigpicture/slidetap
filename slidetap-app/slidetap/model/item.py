import dataclasses
from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID

from slidetap.model.attribute import Attribute
from slidetap.model.image_status import ImageStatus
from slidetap.model.item_reference import ItemReference


@dataclass(frozen=True)
class Item:
    uid: UUID
    identifier: str
    name: Optional[str]
    pseudonym: Optional[str]
    selected: bool
    valid: Optional[bool]
    valid_attributes: Optional[bool]
    valid_relations: Optional[bool]
    attributes: Dict[str, Attribute]
    project_uid: UUID
    schema_display_name: str
    schema_uid: UUID

    @property
    def reference(self) -> ItemReference:
        return ItemReference(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            schema_display_name=self.schema_display_name,
            schema_uid=self.schema_uid,
        )


@dataclass(frozen=True)
class Observation(Item):
    item: Optional[ItemReference] = None


@dataclass(frozen=True)
class Annotation(Item):
    image: Optional[ItemReference] = None
    obseration: List[ItemReference] = dataclasses.field(default_factory=list)


@dataclass(frozen=True)
class ImageFile:
    uid: UUID
    filename: str


@dataclass(frozen=True)
class Image(Item):
    status: ImageStatus
    external_identifier: Optional[str] = None
    folder_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status_message: Optional[str] = None
    files: List[ImageFile] = dataclasses.field(default_factory=list)
    samples: List[ItemReference] = dataclasses.field(default_factory=list)
    annotations: List[ItemReference] = dataclasses.field(default_factory=list)
    observations: List[ItemReference] = dataclasses.field(default_factory=list)


@dataclass(frozen=True)
class Sample(Item):
    parents: List[ItemReference] = dataclasses.field(default_factory=list)
    children: List[ItemReference] = dataclasses.field(default_factory=list)
    images: List[ItemReference] = dataclasses.field(default_factory=list)
    observations: List[ItemReference] = dataclasses.field(default_factory=list)
