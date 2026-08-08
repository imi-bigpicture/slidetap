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

"""Hierarchy layout model for reading the structure under an item."""

from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.table import AttributeValueField


class HierarchyAttributeLayout(FrozenBaseModel):
    """An attribute to show for an item, and which of its values to show."""

    tag: str

    field: AttributeValueField = AttributeValueField.DISPLAY
    """Which value to read: the mapped one, or the one the item was given as."""


class HierarchyLevelLayout(FrozenBaseModel):
    """One kind of item in the tree, and what to say about it."""

    schema_uid: UUID

    attributes: list[HierarchyAttributeLayout] = Field(default_factory=list)
    """What to show for an item of this level, in the order given. Also what
    the tree can be searched by."""

    inline: bool = False
    """Show items of this level beside their parent rather than under it.

    For a level that holds about one item per parent, where a place of its own
    would repeat the parent for every item it holds. A level that is not inline
    is shown in a place of its own."""

    movable: bool = False
    """Whether an item of this level may be dragged onto another item. Where it
    may be dropped comes from the relations between the schemas."""


class HierarchyLayout(FrozenBaseModel):
    """The tree under one kind of item, level by level.

    A level not named is not shown, and neither is anything under it.
    """

    uid: UUID
    """Identity of the layout, which a client asks for it by. Fixed in the
    application's model rather than generated, since it is part of the request
    for the tree and of what a client caches it under."""

    name: str
    display_name: str

    schema_uid: UUID
    """Schema of the item the tree is built from. The item itself is not part
    of the tree, only what hangs under it."""

    levels: list[HierarchyLevelLayout] = Field(default_factory=list)
