from typing import Any, Dict

from marshmallow import fields, post_load

from slidetap.model.table import TableRequest
from slidetap.serialization.base import BaseModel


class TableRequestModel(BaseModel):
    start = fields.Integer()
    size = fields.Integer()
    identifier_filter = fields.String(allow_none=True)
    attribute_filters = fields.Dict(
        keys=fields.String(), values=fields.String(), allow_none=True
    )
    included = fields.Boolean(allow_none=True)
    valid = fields.Boolean(allow_none=True)

    def load(self, data: Dict[str, Any], **kwargs) -> TableRequest:
        loaded = super().load(data, **kwargs)
        assert isinstance(loaded, TableRequest)
        return loaded

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> TableRequest:
        return TableRequest(**data)
