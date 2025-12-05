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

from slidetap.external_interfaces import MetadataExportInterface
from slidetap.model import Dataset, Item, ItemSchema, Project
from slidetap.services import DatabaseService, SchemaService, StorageService

from slidetap_example.metadata_serializer import JsonMetadataSerializer


class ExampleMetadataExportInterface(MetadataExportInterface):
    def __init__(
        self,
        database_service: DatabaseService,
        schema_service: SchemaService,
        storage_service: StorageService,
    ):
        self._serializer = JsonMetadataSerializer()
        self._database_service = database_service
        self._root_schema = schema_service.root
        self._storage = storage_service

    def preview_item(self, item: Item) -> Optional[str]:
        return self._dict_to_json(self._serializer.serialize_item(item))

    def export(self, project: Project, dataset: Dataset) -> None:
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
                item_schema.name: [
                    item.model
                    for item in self._database_service.get_items(
                        session,
                        schema=item_schema,
                        dataset=project.dataset_uid,
                        selected=True,
                    )
                ]
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
