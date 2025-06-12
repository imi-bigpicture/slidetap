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

from typing import Dict, Optional
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import CamelCaseBaseModel


class Dataset(CamelCaseBaseModel):
    uid: UUID
    name: str
    schema_uid: UUID
    valid_attributes: Optional[bool] = None
    attributes: Dict[str, AnyAttribute] = Field(default_factory=dict)
