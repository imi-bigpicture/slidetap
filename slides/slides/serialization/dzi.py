from marshmallow import fields
from slides.serialization.base import BaseModel


class DziModel(BaseModel):
    url = fields.String()
    width = fields.Integer()
    height = fields.Integer()
    tile_size = fields.Integer()
    tile_format = fields.String()
    planes = fields.List(fields.Float)
    channels = fields.List(fields.String)
    tile_overlap = fields.Integer(dump_default=0)
    tiles_url = fields.List(fields.String)
