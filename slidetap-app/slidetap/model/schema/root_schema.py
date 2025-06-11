from typing import Dict
from uuid import UUID

from pydantic import Field
from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.model.schema.project_schema import DatasetSchema, ProjectSchema


class RootSchema(FrozenBaseModel):
    uid: UUID
    name: str
    project: ProjectSchema
    dataset: DatasetSchema
    images: Dict[UUID, ImageSchema] = Field(default_factory=dict)
    samples: Dict[UUID, SampleSchema] = Field(default_factory=dict)
    observations: Dict[UUID, ObservationSchema] = Field(default_factory=dict)
    annotations: Dict[UUID, AnnotationSchema] = Field(default_factory=dict)
