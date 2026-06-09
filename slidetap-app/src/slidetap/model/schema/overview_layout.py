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

"""Overview layout model for cross-item attribute views."""

from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.schema.attribute_schema import Breakpoint


class OverviewSectionLayout(FrozenBaseModel):
    """A single section within an overview layout.

    Each section targets a specific item schema and defines which attributes
    to display and how to group them.
    """

    # Schema of items whose attributes we want to view/edit
    schema_uid: UUID

    # Schema UIDs for traversal from the overview root to the parent items.
    # The last element is the parent schema that groups the target items.
    # E.g. for case → specimen → block → observation:
    # path = [specimen_uid, block_uid] (block is parent, observation is target)
    # For case → specimen → observation:
    # path = [specimen_uid] (specimen is parent)
    # For case-level (parent is root):
    # path = [] (root is parent)
    path: list[UUID] = Field(default_factory=list)

    # Attribute tags to display (empty = show all)
    attributes: list[str] = Field(default_factory=list)

    # Private attribute tags to display (empty = show all)
    private_attributes: list[str] = Field(default_factory=list)

    # Display name for this section
    display_name: str = ""

    # Whether items in this section can be reassigned to different parents via drag
    reassignable: bool = False

    # Whether new items of this schema can be added under a parent in the section
    creatable: bool = False

    # Whether items of this schema can be copied to a different parent
    copyable: bool = False

    # Tags of attributes (or private attributes) that should render collapsed
    # initially. The body is hidden behind a click-to-expand toggle. Useful for
    # bulky attributes (e.g. long report text) that would otherwise dominate
    # the page. Tags not in this list render expanded by default.
    default_collapsed: list[str] = Field(default_factory=list)

    # Layout: width per breakpoint (12-column grid), expand to fill row
    width: dict[Breakpoint, int] = Field(default_factory=lambda: {"xs": 12})
    expand: bool = False

    @property
    def parent_schema_uid(self) -> UUID | None:
        """The parent schema UID — last element of path, or None if path is empty."""
        return self.path[-1] if self.path else None


class OverviewLayout(FrozenBaseModel):
    """Defines an overview layout for viewing and editing attributes across
    descendant items, grouped by an intermediate level in the hierarchy.

    For example, viewing diagnose codes from diagnosis observations across
    all specimens in a case.
    """

    uid: UUID
    name: str
    display_name: str

    # Schema UID of the top-level parent item (e.g. Case)
    schema_uid: UUID

    # Sections defining what to show
    sections: list[OverviewSectionLayout] = Field(default_factory=list)
