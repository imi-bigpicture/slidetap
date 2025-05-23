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


class ProjectValidationModel(BaseModel):
    valid = fields.Boolean()
    uid = fields.UUID()
    non_valid_attributes = fields.List(fields.String())


class DatasetValidationModel(BaseModel):
    valid = fields.Boolean()
    uid = fields.UUID()
    non_valid_attributes = fields.List(fields.String())


class BatchValidationModel(BaseModel):
    valid = fields.Boolean()
    uid = fields.UUID()
    non_valid_items = fields.List(fields.UUID())
