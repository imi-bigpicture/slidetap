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

from marshmallow import fields
from slidetap.serialization.base import BaseModel


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
