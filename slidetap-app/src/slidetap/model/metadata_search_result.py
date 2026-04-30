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

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

from slidetap.model.item import Item


@dataclass(frozen=True)
class MetadataSearchResult:
    """One self-contained unit of metadata import.

    Maps 1:1 to a row in the metadata_search_item table. On success
    ``items`` holds the unit's items in dependency order, ``item_uid``
    points to the entry-level item, and ``failure_message`` is None. On
    failure ``items`` is empty, ``item_uid`` is None, and
    ``failure_message`` describes why.

    Items must be in dependency order: parents before children (Samples
    in hierarchy order, Images after parent Samples, Annotations after
    their Images, Observations after the item they reference). Relations
    to items not yet in the session are silently dropped.
    """

    identifier: str
    schema_uid: UUID
    items: List[Item] = field(default_factory=list)
    item_uid: Optional[UUID] = None
    failure_message: Optional[str] = None

    @classmethod
    def succeeded(
        cls,
        identifier: str,
        schema_uid: UUID,
        items: List[Item],
        item_uid: Optional[UUID] = None,
    ) -> "MetadataSearchResult":
        """Construct a successful result.

        ``item_uid`` should be set to the UID of the entry-level item for
        per-unit importers (e.g. one being per case). Atomic file-parse
        importers that produce one result for a whole file may omit it,
        in which case the search-item row records the success without
        linking to a single item.
        """
        return cls(
            identifier=identifier,
            schema_uid=schema_uid,
            items=items,
            item_uid=item_uid,
        )

    @classmethod
    def failed(
        cls,
        identifier: str,
        schema_uid: UUID,
        message: str,
    ) -> "MetadataSearchResult":
        return cls(
            identifier=identifier,
            schema_uid=schema_uid,
            failure_message=message,
        )

    @property
    def is_failure(self) -> bool:
        return self.failure_message is not None
