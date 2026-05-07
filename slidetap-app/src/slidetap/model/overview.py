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

"""Models for overview data views."""

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import CamelCaseBaseModel


class OverviewItem(CamelCaseBaseModel):
    item_uid: UUID
    identifier: str
    pseudonym: Optional[str] = None
    attributes: Dict[str, AnyAttribute] = Field(default_factory=dict)
    private_attributes: Dict[str, AnyAttribute] = Field(default_factory=dict)


class OverviewSection(CamelCaseBaseModel):
    item_uid: UUID
    label: str
    pseudonym: Optional[str] = None
    schema_uid: UUID
    items: List[OverviewItem] = Field(default_factory=list)


class OverviewRoot(CamelCaseBaseModel):
    item_uid: UUID
    identifier: str
    pseudonym: Optional[str] = None
    sections: List[OverviewSection] = Field(default_factory=list)
    previous_uid: Optional[UUID] = None
    next_uid: Optional[UUID] = None


class RelationChange(CamelCaseBaseModel):
    item_uid: UUID
    target_item_uid: UUID
    source_item_uid: Optional[UUID] = None


class ChangeRelationsRequest(CamelCaseBaseModel):
    changes: List[RelationChange] = Field(default_factory=list)
