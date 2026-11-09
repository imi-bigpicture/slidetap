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

"""How the items of a root are grouped by what they share."""

from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Mapping, Sequence
from uuid import UUID

from slidetap.model import AnyItem
from slidetap.model.item_grouping import ItemGroups


class ItemGrouper(metaclass=ABCMeta):
    """Groups the items of one root by its `ItemGroupingPolicy`, given by
    `SchemaInterface.item_grouper_of()`.

    What an item is grouped by, and what a group counts, is the
    application's: it can be read from other items than those grouped, such
    as the observations on a specimen or the patient over it. So the grouper
    names the schemas it reads, and is given their selected items in the
    project, or the batch, being grouped.
    """

    @abstractmethod
    def schema_uids(self) -> Collection[UUID]:
        """The item schemas whose items `group()` is given. Includes the
        schema of the policy, and only schemas of the root."""
        raise NotImplementedError()

    @abstractmethod
    def group(self, items: Mapping[UUID, Sequence[AnyItem]]) -> ItemGroups:
        """Group the items of the policy's schema.

        Parameters
        ----------
        items: Mapping[UUID, Sequence[AnyItem]]
            The selected items of each schema of `schema_uids()`, by schema
            uid.

        Returns
        -------
        ItemGroups
            The groups, and the items grouped in none.
        """
        raise NotImplementedError()
