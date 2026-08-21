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

"""Model for what hangs under an item."""

from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.item_value_type import ItemValueType


class HierarchyNode(CamelCaseBaseModel):
    """One item in the tree under a root, with whatever hangs under it."""

    uid: UUID
    identifier: str
    name: str | None = None
    """What the item is called under its parent, where an importer set one."""
    pseudonym: str | None = None
    schema_uid: UUID
    schema_display_name: str
    item_value_type: ItemValueType
    valid: bool
    orphan: bool = False
    """Reached through an orphan relation, so it is here for want of anywhere
    better."""
    selected: bool = True
    """Whether the item is still part of the project.

    Shown rather than left out: taking something out of the project is
    reversible, and the row it was taken out from is where it is put back."""
    locked: bool = False
    """Whether the item's batch has been locked.

    What a locked batch holds is what its bundle holds, so whether the item is
    part of the project is no longer one of the things left to decide about it.
    Carried on the row so that what cannot be done is not offered."""
    attributes: dict[str, AnyAttribute] = Field(default_factory=dict)
    """The attributes the layout asks for, in the order it asks for them."""
    children: list["HierarchyNode"] = Field(default_factory=list)
