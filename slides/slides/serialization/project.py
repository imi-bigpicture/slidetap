from marshmallow import fields

from slides.model import ProjectStatus
from slides.serialization.base import BaseModel
from slides.serialization.schema import ItemSchemaModel


class ProjectModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    status = fields.Enum(ProjectStatus, by_value=True)
    item_schemas = fields.List(fields.Nested(ItemSchemaModel))
    item_counts = fields.List(fields.Integer)


class ProjectSimplifiedModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    status = fields.Enum(ProjectStatus)
