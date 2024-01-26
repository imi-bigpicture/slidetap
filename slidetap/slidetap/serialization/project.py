from marshmallow import fields

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


class ProjectSimplifiedModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    status = fields.Enum(ProjectStatus)
