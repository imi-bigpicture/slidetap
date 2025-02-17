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
from slidetap.exporter.metadata_exporter import BackgroundMetadataExporter
from slidetap.model.item import Item
from slidetap.model.schema.root_schema import RootSchema
from slidetap.storage.storage import Storage
from slidetap.task.scheduler import Scheduler


class JsonMetadataExporter(BackgroundMetadataExporter):
    def __init__(self, root_schema: RootSchema, scheduler: Scheduler, storage: Storage):
        self._serializer = JsonMetadataSerializer()
        super().__init__(root_schema, scheduler, storage)

    def preview_item(self, item: Item) -> str:
        return self._dict_to_json(self._serializer.serialize_item(item))

    def _dict_to_json(self, data: Mapping[str, Any]) -> str:
        return json.dumps(data, indent=4)
