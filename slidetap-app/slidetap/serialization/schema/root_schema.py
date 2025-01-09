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

from typing import Any, Dict

from marshmallow import fields, post_load
from slidetap.model.schema.project_schema import ProjectSchema
from slidetap.serialization.base import BaseModel
from slidetap.serialization.schema.item_schema import (
    AnnotationSchemaModel,
    ImageSchemaModel,
    ObservationSchemaModel,
    SampleSchemaModel,
)


class RootSchemaModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    project = fields.Nested("ProjectSchemaModel", required=True)
    samples = fields.Dict(fields.UUID, fields.Nested(SampleSchemaModel), required=True)
    images = fields.Dict(fields.UUID, fields.Nested(ImageSchemaModel), required=True)
    observations = fields.Dict(
        fields.UUID, fields.Nested(ObservationSchemaModel), required=True
    )
    annotations = fields.Dict(
        fields.UUID, fields.Nested(AnnotationSchemaModel), required=True
    )

    def load(self, data: Dict[str, Any], **kwargs) -> ProjectSchema:
        return super().load(data, **kwargs)  # type: ignore

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> ProjectSchema:
        return ProjectSchema(**data)
