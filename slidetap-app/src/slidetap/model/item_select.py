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

from enum import Enum
from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.item_value_type import ItemValueType


class ItemSelect(CamelCaseBaseModel):
    """Putting an item into the project or taking it out, and how far what
    follows it is allowed to reach.

    Left at their defaults, the cascade options follow every relation the
    schema says must follow. Narrowing them lets a curator stop the cascade at
    a direction or at kinds of items; what that leaves short of its schema is
    marked as not valid, to be settled before the batch completes.
    """

    select: bool
    comment: str | None = None
    tags: list[UUID] | None = None
    additive_tags: bool = False
    cascade_up: bool = True
    """Follow relations to what the item hangs under: a sample's parents, an
    image's samples, an annotation's image, an observation's subject."""
    cascade_down: bool = True
    """Follow relations to what hangs under the item: a sample's children,
    images and observations, an image's annotations and observations, an
    annotation's observations."""
    skip_schemas: list[UUID] = Field(default_factory=list)
    """Item schemas the cascade leaves as they are, wherever it meets them."""
    override_curation: bool = False
    """When selecting, also bring back what a curator took out by name. Left
    false, those stay out and are reported."""
    dry_run: bool = False
    """Work out what would change and report it, changing nothing."""


class CascadeDirection(Enum):
    """How an item came to change with the one that was asked for."""

    ITEM = "item"
    """The item the request named."""
    UP = "up"
    """Reached from something that hangs under it."""
    DOWN = "down"
    """Reached from something it hangs under."""


class SelectionChange(CamelCaseBaseModel):
    """One item whose selection a request changed, or would change."""

    uid: UUID
    identifier: str
    schema_uid: UUID
    item_value_type: ItemValueType
    selected: bool
    """Whether the item is in the project after the change."""
    direction: CascadeDirection
    overrode_curation: bool = False
    """A curator had taken the item out by name, and the change brought it
    back because it was asked to."""


class ItemSelectResult(CamelCaseBaseModel):
    """What a selection changed, or in a dry run would change."""

    changed: list[SelectionChange] = Field(default_factory=list)
    """Every item whose selection flipped, the named item first."""
    kept_out: list[SelectionChange] = Field(default_factory=list)
    """Items the cascade would have brought back but left out, because a
    curator had taken them out by name and overriding that was not asked
    for."""
    left_invalid: list[SelectionChange] = Field(default_factory=list)
    """Items in the project after the change whose relations are not
    satisfied, among those that changed and what they are related to. Each is
    listed with the direction it lies in from the change that reached it, or
    as the item itself."""
    dry_run: bool = False
