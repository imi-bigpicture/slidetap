from marshmallow import fields

from slides.serialization.base import BaseModel


class BasicAuthModel(BaseModel):
    username = fields.String(required=True)
    password = fields.String(required=True)
