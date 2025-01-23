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


from typing import Optional
from uuid import UUID

from slidetap.database import DatabaseItem
from slidetap.exporter import MetadataExporter


class PreviewService:
    def __init__(
        self,
        metadata_exporter: MetadataExporter,
    ) -> None:
        self.metadata_exporter = metadata_exporter

    def get_preview(self, item_uid: UUID) -> Optional[str]:
        item = DatabaseItem.get_optional(item_uid)
        if item is None:
            return None
        return self.metadata_exporter.preview_item(item.model)
