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
    images: Dict[str, ImageSchema]
    samples: Dict[str, SampleSchema]
    observations: Dict[str, ObservationSchema]
    annotations: Dict[str, AnnotationSchema]
