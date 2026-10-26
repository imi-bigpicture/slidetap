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
from slidetap.model.schema.attribute_value_layout import AttributeValueLayout


class SampleForImageLayout(FrozenBaseModel):
    """A sample a curator may make for an image that is parked, by dropping
    the image on the item the new sample is to hang under.

    For an image the import found nothing to put it on: a scan the laboratory
    never registered a slide for has no slide to be moved to, and making one
    is the only way to put it where it belongs. Offered only for a parked
    image, since one already on a sample has somewhere to be.
    """

    sample_schema_uid: UUID
    """Schema of the sample to make. The image's schema has to relate to it."""

    parent_schema_uid: UUID
    """Schema of the item the image is dropped on, which the new sample hangs
    under. The sample's schema has to relate to it."""

    mappable_values: dict[str, str] = Field(default_factory=dict)
    """Which attribute of the image fills which attribute of the sample, by
    tag: the sample's attribute at the key, the image's at the value.

    Given to the sample as its mappable value, which mapping then resolves as
    it would what an import left: what the image was filed under elsewhere is
    usually spelled the way the sample's own value would have been. The
    image's attribute is looked up in both its attributes and its private
    attributes."""


class HierarchyLevelLayout(FrozenBaseModel):
    """One kind of item in the tree, and what to say about it."""

    schema_uid: UUID

    attributes: list[AttributeValueLayout] = Field(default_factory=list)
    """What to show for an item of this level, in the order given. Also what
    the tree can be searched by.

    Looked up in both the attributes and the private attributes of the item:
    the level shows what it names, and what an item was filed under elsewhere
    is often the only thing that says where it belongs."""

    inline: bool = False
    """Show items of this level beside their parent rather than under it.

    For a level that holds about one item per parent, where a place of its own
    would repeat the parent for every item it holds. A level that is not inline
    is shown in a place of its own."""

    movable: bool = False
    """Whether an item of this level may be dragged onto another item. Where it
    may be dropped comes from the relations between the schemas."""

    deletable: bool = False
    """Whether an item of this level may be taken out of the project from the
    tree, and put back the same way.

    Offered only for an item nothing hangs under: what a level shows is one row
    of a case, and a row that stands for something with children takes them
    with it, which is not a thing to decide from a row. A slide the laboratory
    registered and nobody scanned is what this is for -- it is in the tree
    because LIS says so, and only a curator can say it is not part of the
    dataset."""

    sample_for_image: SampleForImageLayout | None = None
    """For a level of images: the sample a parked image of it may be given, by
    dropping it on an item of the sample's parent schema. None where no sample
    is made from the tree."""


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
