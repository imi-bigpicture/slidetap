#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from typing import Dict
from uuid import UUID

from pydantic import Field
from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.schema.dataset_schema import DatasetSchema
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.model.schema.project_schema import ProjectSchema


class RootSchema(FrozenBaseModel):
    uid: UUID
    name: str
    project: ProjectSchema
    dataset: DatasetSchema
    images: Dict[UUID, ImageSchema] = Field(default_factory=dict)
    samples: Dict[UUID, SampleSchema] = Field(default_factory=dict)
    observations: Dict[UUID, ObservationSchema] = Field(default_factory=dict)
    annotations: Dict[UUID, AnnotationSchema] = Field(default_factory=dict)
