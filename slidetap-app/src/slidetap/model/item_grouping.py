#    Copyright 2026 SECTRA AB
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

"""The groups items fall into by what they share, see `ItemGroupingPolicy`."""

from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.item_identity import ItemIdentity
from slidetap.model.schema.item_grouping_policy import ItemGroupingPolicy


class ItemGroupValuePart(FrozenBaseModel):
    """One of what a value of a group is made of, such as one diagnose of a
    set of them, shown as a chip with its description on hover."""

    label: str
    description: str | None = None
    """Shown on hover, such as the code a meaning is of."""


class ItemGroup(FrozenBaseModel):
    """Items sharing their values, as the application grouped them."""

    values: list[str]
    """What the items share, as shown, one per column of the grouping."""

    parts: list[list[ItemGroupValuePart]] = Field(default_factory=list)
    """What each value is made of, one list per column, each part shown as a
    chip. Empty, or empty for a column, where the value is shown as its text.
    The text is what the groups are sorted, filtered and told apart by."""

    item_uids: list[UUID]

    count: int
    """How many of what the policy counts the items are of, e.g. patients.
    Can be fewer than the items: one patient can have several."""


class IncompleteItem(FrozenBaseModel):
    """An item in no group, as it lacks a value grouped by."""

    item_uid: UUID

    missing: list[str]
    """The columns the item has no value for, as shown."""


class ItemGroups(FrozenBaseModel):
    """The groups of the items given, as the application works them out."""

    columns: list[str]
    """What the items are grouped by, as shown, in the order of the values of
    each group."""

    groups: list[ItemGroup]

    incomplete: list[IncompleteItem]


class ItemGroupSummary(FrozenBaseModel):
    """A group, with its items named, as it is listed."""

    values: list[str]
    parts: list[list[ItemGroupValuePart]] = Field(default_factory=list)
    """What each value is made of, see `ItemGroup.parts`."""
    items: list[ItemIdentity]
    count: int

    review_unit_uids: list[UUID] = Field(default_factory=list)
    """The review units the items are answered for in, such as their cases, each
    once. Empty where the root reviews nothing above the items."""

    below_minimum: bool
    """Whether the group holds fewer than the policy asks for."""


class IncompleteGroupedItem(FrozenBaseModel):
    """An item in no group, named, as it is listed."""

    item: ItemIdentity
    missing: list[str]


class ItemGrouping(FrozenBaseModel):
    """The groups of the selected items of a project, or of one of its
    batches, smallest first."""

    policy: ItemGroupingPolicy

    batch_uid: UUID | None
    """The batch the items are of, None where they are of the whole project."""

    columns: list[str]
    groups: list[ItemGroupSummary]
    incomplete: list[IncompleteGroupedItem]
