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

from marshmallow import fields, pre_load

from slidetap.model import ProjectStatus
from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.base import BaseModel
from slidetap.serialization.schema import ItemSchemaOneOfModel, ProjectSchemaModel


class ProjectItemModel(BaseModel):
    schema = fields.Nested(ItemSchemaOneOfModel)
    count = fields.Integer()


class ProjectModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    status = fields.Enum(ProjectStatus, by_value=True)
    items = fields.List(fields.Nested(ProjectItemModel))
    attributes = fields.Dict(keys=fields.String(), values=fields.Nested(AttributeModel))
    schema = fields.Nested(ProjectSchemaModel)

    @pre_load
    def pre_load(self, data, **kwargs):
        data.pop("items", None)
        return data


class ProjectSimplifiedModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    status = fields.Enum(ProjectStatus)
