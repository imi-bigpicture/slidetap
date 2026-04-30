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

from datetime import datetime
from typing import Optional
from uuid import UUID

from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.metadata_import_status import MetadataImportStatus


class MetadataSearchItem(CamelCaseBaseModel):
    """One per-unit metadata import outcome.

    Lives in the metadata_search_item table — separate from real items.
    Failed attempts have item_uid=None; successful attempts link to the
    entry-level item that was created. Cascade-deletes when the linked
    item is removed via curate.
    """

    uid: UUID
    batch_uid: UUID
    identifier: str
    schema_uid: UUID
    status: MetadataImportStatus = MetadataImportStatus.NOT_STARTED
    message: Optional[str] = None
    item_uid: Optional[UUID] = None
    attempted_at: Optional[datetime] = None
    retry_count: int = 0
