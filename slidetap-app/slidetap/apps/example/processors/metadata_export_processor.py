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
from typing import Iterable
from uuid import UUID

from slidetap.apps.example.metadata_serializer import JsonMetadataSerializer
from slidetap.config import Config
from slidetap.model.schema.item_schema import ItemSchema
from slidetap.model.schema.root_schema import RootSchema
from slidetap.storage.storage import Storage
from slidetap.task.processors.metadata.metadata_export_processor import (
    MetadataExportProcessor,
)


class JsonMetadataExportProcessor(MetadataExportProcessor):
    def __init__(self, root_schema: RootSchema, storage: Storage, config: Config):
        self._serializer = JsonMetadataSerializer()
        self._storage = storage
        super().__init__(root_schema, config)

    def run(self, project_uid: UUID):
        with self._database_service.get_session() as session:
            project = self._database_service.get_project(session, project_uid)
            try:
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
                    self._storage.store_metadata(
                        project.model, {"metadata.json": output_stream}
                    )
                logging.info(f"Exported project {project}.")
                self._project_service.set_as_export_complete(project_uid, session)
            except Exception:
                logging.error(f"Failed to export project {project}.", exc_info=True)
