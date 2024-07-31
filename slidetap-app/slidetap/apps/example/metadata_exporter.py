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

"""Json exporter for metadata."""
import json
from typing import Any, Mapping

from slidetap.apps.example.metadata_serializer import JsonMetadataSerializer
from slidetap.database.project import Item
from slidetap.storage.storage import Storage
from slidetap.task.scheduler import Scheduler
from slidetap.web.exporter.metadata_exporter import BackgroundMetadataExporter


class JsonMetadataExporter(BackgroundMetadataExporter):
    def __init__(self, scheduler: Scheduler, storage: Storage):
        self._serializer = JsonMetadataSerializer()
        super().__init__(scheduler, storage)

    def preview_item(self, item: Item) -> str:
        return self._dict_to_json(self._serializer.serialize_item(item.project, item))

    def _dict_to_json(self, data: Mapping[str, Any]) -> str:
        return json.dumps(data, indent=4)
