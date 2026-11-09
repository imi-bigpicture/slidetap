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

"""How the items of a project are grouped by what they share, and how many a
group must hold."""

from uuid import UUID

from pydantic import Field, model_validator

from slidetap.model.base_model import FrozenBaseModel


class ItemGroupingPolicy(FrozenBaseModel):
    """The items of a schema grouped by values they share, each group to hold
    at least a number of something, such as patients.

    Meant for the values that could single someone out of a dataset, e.g. a
    diagnose, a site and an age bucket: a dataset is often selected so that
    every such group is large enough, and curating can move an item into a
    group too small. Which values an item is grouped by, and what is counted,
    is worked out by the `ItemGrouper` the application gives for the root
    from `SchemaInterface.item_grouper_of()`; the policy says what the result
    is checked against and how it is shown.

    Declared by the application, as the size a group must have is a decision
    about the dataset. It changes nothing stored, so it can be changed under
    the same root.
    """

    schema_uid: UUID
    """The item schema whose items are grouped."""

    minimum_count: int = Field(ge=1)
    """The fewest a group is to hold of what is counted."""

    close_count: int | None = Field(default=None, ge=1)
    """The most a group can hold and still be shown as close to the minimum,
    worth watching as a correction or two can take it under. At least the
    minimum. None where no group is shown as close."""

    count_display_name: str = "Items"
    """What is counted in a group, as shown, e.g. "Patients"."""

    display_name: str = "Groups"
    """What the groups are called where they are listed."""

    @model_validator(mode="after")
    def _close_from_the_minimum(self) -> "ItemGroupingPolicy":
        if self.close_count is not None and self.close_count < self.minimum_count:
            raise ValueError(
                f"close_count {self.close_count} is below minimum_count "
                f"{self.minimum_count}: a group that close is too small."
            )
        return self
