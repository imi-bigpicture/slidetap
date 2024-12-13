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
from typing import Iterable
from uuid import UUID

from flask import current_app
from slidetap.apps.example.metadata_serializer import JsonMetadataSerializer
from slidetap.apps.example.schema import ExampleSchema
from slidetap.model.schema.item_schema import ItemSchema
from slidetap.storage.storage import Storage
from slidetap.task.processors.metadata.metadata_export_processor import (
    MetadataExportProcessor,
)


class JsonMetadataExportProcessor(MetadataExportProcessor):
    def __init__(self, storage: Storage):
        self._serializer = JsonMetadataSerializer()
        self._storage = storage
        self._schema = ExampleSchema()

    def run(self, project_uid: UUID):
        with self._app.app_context():
            project = self._project_service.get(project_uid)
            try:
                item_schemas: Iterable[ItemSchema] = [
                    schema
                    for schema_type in [
                        self._schema.samples.values(),
                        self._schema.images.values(),
                        self._schema.annotations.values(),
                        self._schema.observations.values(),
                    ]
                    for schema in schema_type
                ]
                data = {
                    item_schema.name: self._database_service.get_project_items(
                        project_uid, item_schema, selected=True
                    )
                    for item_schema in item_schemas
                }
                with io.StringIO() as output_stream:
                    output_stream.write(json.dumps(data))
                    self._storage.store_metadata(
                        project, {"metadata.json": output_stream}
                    )
                current_app.logger.info(f"Exported project {project}.")
                self._project_service.set_as_export_complete(project_uid)
            except Exception:
                current_app.logger.error(
                    f"Failed to export project {project}.", exc_info=True
                )
