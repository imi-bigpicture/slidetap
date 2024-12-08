from dataclasses import dataclass
from typing import Dict, Tuple
from uuid import UUID

from slidetap.model.schema.attribute_schema import AttributeSchema
from slidetap.model.schema.item_relation import (
    AnnotationToImageRelation,
    ImageToSampleRelation,
    ObservationToAnnotationRelation,
    ObservationToImageRelation,
    ObservationToSampleRelation,
    SampleToSampleRelation,
)


@dataclass(frozen=True)
class ItemSchema:
    uid: UUID
    name: str
    display_name: str
    display_order: int
    attributes: Dict[str, AttributeSchema]


@dataclass(frozen=True)
class ObservationSchema(ItemSchema):
    samples: Tuple[ObservationToSampleRelation, ...]
    images: Tuple[ObservationToImageRelation, ...]
    annotations: Tuple[ObservationToAnnotationRelation, ...]


@dataclass(frozen=True)
class AnnotationSchema(ItemSchema):
    images: Tuple[AnnotationToImageRelation, ...]
    oberservations: Tuple[ObservationToAnnotationRelation, ...]


@dataclass(frozen=True)
class ImageSchema(ItemSchema):
    samples: Tuple[ImageToSampleRelation, ...]
    observations: Tuple[ObservationToImageRelation, ...]
    annotations: Tuple[AnnotationToImageRelation, ...]


@dataclass(frozen=True)
class SampleSchema(ItemSchema):
    children: Tuple[SampleToSampleRelation, ...]
    parents: Tuple[SampleToSampleRelation, ...]
    images: Tuple[ImageToSampleRelation, ...]
    observations: Tuple[ObservationToSampleRelation, ...]
