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

from slidetap.model import ProjectStatus
from slidetap.model.project import Project
from slidetap.serialization.attribute import AttributeDictField
from slidetap.serialization.base import BaseModel


class ProjectModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    status = fields.Enum(ProjectStatus, by_value=True)
    valid_attributtes = fields.Boolean()
    attributes = AttributeDictField()
    root_schema_uid = fields.UUID(required=True)
    schema_uid = fields.UUID(required=True)
    dataset_uid = fields.UUID(required=True)
    locked = fields.Boolean()
    created = fields.DateTime(required=True)

    def load(self, data: Dict[str, Any], **kwargs) -> Project:
        return super().load(data, **kwargs)  # type: ignore

    @post_load
    def post_load(self, data, **kwargs):
        return Project(**data)
