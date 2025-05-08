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

import io
import json
import logging
from typing import Any, Iterable, Mapping, Optional

from slidetap.apps.example.metadata_serializer import JsonMetadataSerializer
from slidetap.external_interfaces import MetadataExportInterface
from slidetap.model import Item, ItemSchema, Project
from slidetap.service_provider import ServiceProvider


class ExampleMetadataExportInterface(MetadataExportInterface):
    def __init__(self, service_provider: ServiceProvider):
        self._serializer = JsonMetadataSerializer()
        self._database_service = service_provider.database_service
        self._root_schema = service_provider.schema_service.root
        self._storage = service_provider.storage_service

    def preview_item(self, item: Item) -> Optional[str]:
        return self._dict_to_json(self._serializer.serialize_item(item))

    def export(self, project: Project) -> None:
        item_schemas: Iterable[ItemSchema] = [
            schema
            for schema_type in [
                self._root_schema.samples.values(),
                self._root_schema.images.values(),
                self._root_schema.annotations.values(),
                self._root_schema.observations.values(),
            ]
            for schema in schema_type
        ]
        with self._database_service.get_session() as session:
            data = {
                item_schema.name: self._database_service.get_items(
                    session,
                    project.dataset_uid,
                    schema=item_schema,
                    selected=True,
                )
                for item_schema in item_schemas
            }
        with io.StringIO() as output_stream:
            output_stream.write(
                json.dumps(
                    {
                        name: self._serializer.serialize_items(items)
                        for name, items in data.items()
                    }
                )
            )
            self._storage.store_metadata(project, {"metadata.json": output_stream})
        logging.info(f"Exported project {project}.")

    def _dict_to_json(self, data: Mapping[str, Any]) -> str:
        return json.dumps(data, indent=4)
