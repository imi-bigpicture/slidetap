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

"""Project model."""

import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.project_status import ProjectStatus


class Project(CamelCaseBaseModel):
    """Project containing metadata and image attributes."""

    uid: UUID
    name: str
    root_schema_uid: UUID
    schema_uid: UUID
    dataset_uid: UUID
    created: datetime.datetime
    status: ProjectStatus = ProjectStatus.IN_PROGRESS
    valid_attributes: Optional[bool] = None
    attributes: Dict[str, AnyAttribute] = Field(default_factory=dict)
    mapper_groups: List[UUID] = Field(default_factory=list)
