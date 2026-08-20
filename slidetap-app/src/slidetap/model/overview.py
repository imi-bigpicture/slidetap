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

from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import CamelCaseBaseModel


class OverviewItem(CamelCaseBaseModel):
    item_uid: UUID
    identifier: str
    pseudonym: str | None = None
    attributes: dict[str, AnyAttribute] = Field(default_factory=dict)
    private_attributes: dict[str, AnyAttribute] = Field(default_factory=dict)


class OverviewSection(CamelCaseBaseModel):
    item_uid: UUID
    label: str
    pseudonym: str | None = None
    schema_uid: UUID
    items: list[OverviewItem] = Field(default_factory=list)

    parent_item: OverviewItem | None = None
    """The group's own item, when the section asks for attributes of the item it
    groups by — a specimen's anatomical site alongside its diagnoses, rather
    than in a section of its own. Set only when the section layout names
    ``parent_attributes``."""

    parent_schema_uid: UUID | None = None
    """What the group itself is, which is not the section's ``schema_uid``: the
    section holds a specimen's diagnoses, the group is the specimen. Set
    whenever the section groups by something, whether or not that something's
    own attributes are shown, so a view can say what it is about to act on."""


class OverviewRoot(CamelCaseBaseModel):
    item_uid: UUID
    identifier: str
    pseudonym: str | None = None
    batch_uid: UUID
    sections: list[OverviewSection] = Field(default_factory=list)
    previous_uid: UUID | None = None
    next_uid: UUID | None = None
