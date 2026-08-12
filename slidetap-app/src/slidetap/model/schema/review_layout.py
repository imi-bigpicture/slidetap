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

"""Review layout model for what a reviewer is shown of an item."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.schema.attribute_schema import Breakpoint
from slidetap.model.schema.hierarchy_layout import HierarchyLayout
from slidetap.model.schema.overview_layout import OverviewLayout


class ReviewPanelLayout(FrozenBaseModel):
    """What every panel of a tab has, whatever it shows."""

    width: dict[Breakpoint, int] | None = None
    """How much of the tab the panel takes, out of twelve.

    The panels that do not say divide what the rest leave.
    """


class OverviewPanelLayout(ReviewPanelLayout):
    """A panel showing an overview layout."""

    kind: Literal["overview"] = "overview"
    layout: OverviewLayout


class HierarchyPanelLayout(ReviewPanelLayout):
    """A panel showing a hierarchy layout."""

    kind: Literal["hierarchy"] = "hierarchy"
    layout: HierarchyLayout


class ImagesPanelLayout(ReviewPanelLayout):
    """A panel showing the images under the item, as pictures rather than rows."""

    kind: Literal["images"] = "images"

    group_by_schema_uid: UUID
    """What to group the images by — the schema of the item each group stands
    for, which may be the reviewed item itself."""

    image_schema_uids: list[UUID] = Field(default_factory=list)
    """Which images to show. All of them when not given.

    Given, the panel shows these and does not offer the choice; the grouping
    works the same way.
    """


AnyReviewPanelLayout = Annotated[
    OverviewPanelLayout | HierarchyPanelLayout | ImagesPanelLayout,
    Field(discriminator="kind"),
]


class ReviewTabLayout(FrozenBaseModel):
    """One tab of the review view, and what it puts side by side.

    Panels rather than a single view: a tree is read against the report it was
    made from, and images against what the laboratory says is on them.
    """

    display_name: str | None = None
    """What to call the tab. Taken from its first panel when not given."""

    panels: list[AnyReviewPanelLayout] = Field(default_factory=list)


class ReviewLayout(FrozenBaseModel):
    """What a reviewer is shown of an item, tab by tab.

    The tabs are listed rather than gathered from the layouts that exist, so
    that their order is a decision and a layout can be shown beside another
    without becoming a tab of its own.
    """

    uid: UUID
    name: str
    schema_uid: UUID
    """Schema of the item being reviewed."""

    tabs: list[ReviewTabLayout] = Field(default_factory=list)
