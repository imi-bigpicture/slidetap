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
from slidetap.web.model.table import ColumnSort, TableRequest
from slidetap.web.serialization.base import BaseModel


class ColumnSortModel(BaseModel):
    column = fields.String()
    is_attribute = fields.Boolean()
    descending = fields.Boolean()

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> ColumnSort:
        return ColumnSort(**data)


class TableRequestModel(BaseModel):
    start = fields.Integer()
    size = fields.Integer()
    identifier_filter = fields.String(allow_none=True)
    attribute_filters = fields.Dict(
        keys=fields.String(), values=fields.String(), allow_none=True
    )
    sorting = fields.List(fields.Nested(ColumnSortModel()), allow_none=True)
    included = fields.Boolean(allow_none=True)
    valid = fields.Boolean(allow_none=True)

    def load(self, data: Dict[str, Any], **kwargs) -> TableRequest:
        loaded = super().load(data, **kwargs)
        assert isinstance(loaded, TableRequest)
        return loaded

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> TableRequest:
        return TableRequest(**data)
