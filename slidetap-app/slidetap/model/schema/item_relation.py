from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class ItemSchemaReference:
    uid: UUID
    name: str
    display_name: str


@dataclass(frozen=True)
class ItemRelation:
    uid: UUID
    name: str
    description: Optional[str]


@dataclass(frozen=True)
class SampleToSampleRelation(ItemRelation):
    parent: ItemSchemaReference
    child: ItemSchemaReference
    min_parents: Optional[int]
    max_parents: Optional[int]
    min_children: Optional[int]
    max_children: Optional[int]


@dataclass(frozen=True)
class ImageToSampleRelation(ItemRelation):
    image: ItemSchemaReference
    sample: ItemSchemaReference


@dataclass(frozen=True)
class AnnotationToImageRelation(ItemRelation):
    annotation: ItemSchemaReference
    image: ItemSchemaReference


@dataclass(frozen=True)
class ObservationRelation(ItemRelation):
    observation: ItemSchemaReference


@dataclass(frozen=True)
class ObservationToSampleRelation(ObservationRelation):
    sample: ItemSchemaReference


@dataclass(frozen=True)
class ObservationToImageRelation(ObservationRelation):
    image: ItemSchemaReference


@dataclass(frozen=True)
class ObservationToAnnotationRelation(ObservationRelation):
    annotation: ItemSchemaReference
