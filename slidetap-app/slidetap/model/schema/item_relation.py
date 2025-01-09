from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class ItemRelation:
    uid: UUID
    name: str
    description: Optional[str]


@dataclass(frozen=True)
class SampleToSampleRelation(ItemRelation):
    parent_title: str
    child_title: str
    parent_uid: UUID
    child_uid: UUID
    min_parents: Optional[int]
    max_parents: Optional[int]
    min_children: Optional[int]
    max_children: Optional[int]


@dataclass(frozen=True)
class ImageToSampleRelation(ItemRelation):
    image_title: str
    sample_title: str
    image_uid: UUID
    sample_uid: UUID


@dataclass(frozen=True)
class AnnotationToImageRelation(ItemRelation):
    annotation_title: str
    image_title: str
    annotation_uid: UUID
    image_uid: UUID


@dataclass(frozen=True)
class ObservationRelation(ItemRelation):
    observation_title: str
    observation_uid: UUID


@dataclass(frozen=True)
class ObservationToSampleRelation(ObservationRelation):
    sample_title: str
    sample_uid: UUID


@dataclass(frozen=True)
class ObservationToImageRelation(ObservationRelation):
    image_title: str
    image_uid: UUID


@dataclass(frozen=True)
class ObservationToAnnotationRelation(ObservationRelation):
    annotation_title: str
    annotation_uid: UUID
