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
from uuid import UUID

from flask import current_app
from slidetap.apps.example.metadata_serializer import JsonMetadataSerializer
from slidetap.database.project import Project
from slidetap.database.schema.item_schema import ItemSchema
from slidetap.storage.storage import Storage
from slidetap.tasks.processors.metadata.metadata_export_processor import (
    MetadataExportProcessor,
)


class JsonMetadataExportProcessor(MetadataExportProcessor):
    def __init__(self, storage: Storage):
        self._serializer = JsonMetadataSerializer()
        self._storage = storage

    def run(self, project_uid: UUID):
        with self._app.app_context():
            project = Project.get(project_uid)
            try:
                item_schemas = ItemSchema.get_for_schema(project.root_schema.uid)
                data = {
                    item_schema.name: self._serializer.serialize_items(
                        project, item_schema
                    )
                    for item_schema in item_schemas
                }
                with io.StringIO() as output_stream:
                    output_stream.write(json.dumps(data))
                    self._storage.store_metadata(
                        project, {"metadata.json": output_stream}
                    )
                current_app.logger.info(f"Exported project {project}.")
                project.set_as_export_complete()
            except Exception:
                current_app.logger.error(
                    f"Failed to export project {project}.", exc_info=True
                )
