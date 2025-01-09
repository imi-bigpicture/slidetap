import dataclasses
from dataclasses import dataclass
from typing import Dict
from uuid import UUID

from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.model.schema.project_schema import ProjectSchema


@dataclass(frozen=True)
class RootSchema:
    uid: UUID
    name: str
    project: ProjectSchema
    images: Dict[UUID, ImageSchema] = dataclasses.field(default_factory=dict)
    samples: Dict[UUID, SampleSchema] = dataclasses.field(default_factory=dict)
    observations: Dict[UUID, ObservationSchema] = dataclasses.field(
        default_factory=dict
    )
    annotations: Dict[UUID, AnnotationSchema] = dataclasses.field(default_factory=dict)
