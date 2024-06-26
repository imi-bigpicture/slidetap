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
import io
import json
from typing import Any, List, Mapping

from flask import current_app

from slidetap.database.project import (
    Annotation,
    Image,
    Item,
    Observation,
    Project,
    Sample,
)
from slidetap.database.schema.item_schema import ItemSchema
from slidetap.exporter.metadata.metadata_exporter import MetadataExporter
from slidetap.serialization.item import ItemModelFactory


class JsonMetadataExporter(MetadataExporter):
    def export(self, project: Project):
        current_app.logger.info(f"Exporting project {project}.")
        project.set_as_exporting()
        try:
            item_schemas = ItemSchema.get_for_schema(project.root_schema.uid)
            data = {
                item_schema.name: self._serialize_items(project, item_schema)
                for item_schema in item_schemas
            }
            with io.StringIO() as output_stream:
                output_stream.write(json.dumps(data))
                self.storage.store_metadata(project, {"metadata.json": output_stream})
            current_app.logger.info(f"Exported project {project}.")
            project.set_as_export_complete()
        except Exception:
            current_app.logger.error(
                f"Failed to export project {project}.", exc_info=True
            )

    def preview_item(self, item: Item) -> str:
        return self._dict_to_json(self._serialize_item(item.project, item))

    def _serialize_items(
        self, project: Project, item_schema: ItemSchema
    ) -> List[Mapping[str, Any]]:
        items = Item.get_for_project(project.uid, item_schema.uid, selected=True)
        return [self._serialize_item(project, item) for item in items]

    def _serialize_item(self, project: Project, item: Item) -> Mapping[str, Any]:
        exclude = (
            "project_uid",
            "selected",
            "schema",
            "item_value_type",
            "attributes.uid",
            "attributes.display_value",
            "attributes.mappable_value",
            "attributes.schema",
            "attributes.mapping_status",
        )
        if isinstance(item, Sample):
            exclude += (
                "parents.schema_display_name",
                "parents.schema_uid",
                "children.schema_display_name",
                "children.schema_uid",
                "images.schema_display_name",
                "images.schema_uid",
                "observations.schema_display_name",
                "observations.schema_uid",
            )
        elif isinstance(item, Image):
            exclude += (
                "status",
                "samples.schema_display_name",
                "samples.schema_uid",
            )
        elif isinstance(item, Annotation):
            exclude += (
                "image.schema_display_name",
                "image.schema_uid",
            )
        elif isinstance(item, Observation):
            exclude += (
                "item.schema_display_name",
                "item.schema_uid",
            )
        else:
            raise ValueError(f"Unknown item {item}.")

        model = ItemModelFactory().create(item.schema)
        data = model(exclude=exclude).dump(item)

        assert isinstance(data, Mapping)
        return data

    def _dict_to_json(self, data: Mapping[str, Any]) -> str:
        return json.dumps(data, indent=4)
