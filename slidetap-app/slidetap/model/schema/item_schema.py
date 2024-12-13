import dataclasses
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
    attributes: Dict[str, AttributeSchema] = dataclasses.field(default_factory=dict)


@dataclass(frozen=True)
class ObservationSchema(ItemSchema):
    samples: Tuple[ObservationToSampleRelation, ...] = dataclasses.field(
        default_factory=tuple
    )
    images: Tuple[ObservationToImageRelation, ...] = dataclasses.field(
        default_factory=tuple
    )
    annotations: Tuple[ObservationToAnnotationRelation, ...] = dataclasses.field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class AnnotationSchema(ItemSchema):
    images: Tuple[AnnotationToImageRelation, ...] = dataclasses.field(
        default_factory=tuple
    )
    oberservations: Tuple[ObservationToAnnotationRelation, ...] = dataclasses.field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class ImageSchema(ItemSchema):
    samples: Tuple[ImageToSampleRelation, ...] = dataclasses.field(
        default_factory=tuple
    )
    observations: Tuple[ObservationToImageRelation, ...] = dataclasses.field(
        default_factory=tuple
    )
    annotations: Tuple[AnnotationToImageRelation, ...] = dataclasses.field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class SampleSchema(ItemSchema):
    children: Tuple[SampleToSampleRelation, ...] = dataclasses.field(
        default_factory=tuple
    )
    parents: Tuple[SampleToSampleRelation, ...] = dataclasses.field(
        default_factory=tuple
    )
    images: Tuple[ImageToSampleRelation, ...] = dataclasses.field(default_factory=tuple)
    observations: Tuple[ObservationToSampleRelation, ...] = dataclasses.field(
        default_factory=tuple
    )
