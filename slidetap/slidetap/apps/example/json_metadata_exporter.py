"""Json exporter for metadata."""
import io
import json
from typing import Any, List, Mapping

from slidetap.database.project import Item, Project
from slidetap.database.schema.item_schema import ItemSchema
from slidetap.exporter.metadata.metadata_exporter import MetadataExporter
from slidetap.serialization.item import ItemModelFactory


class JsonMetadataExporter(MetadataExporter):
    def export(self, project: Project):
        item_schemas = ItemSchema.get_for_schema(project.schema.uid)
        data = {
            item_schema.name: self._serialize_items(project, item_schema)
            for item_schema in item_schemas
        }
        with io.StringIO() as output_stream:
            output_stream.write(json.dumps(data))
            self.storage.store_metadata(project, {"metadata.json": output_stream})

    def _serialize_items(
        self, project: Project, item_schema: ItemSchema
    ) -> List[Mapping[str, Any]]:
        items = Item.get_for_project(project.uid, item_schema.uid, True)
        return [self._serialize_item(project, item) for item in items]

    def _serialize_item(self, project: Project, item: Item) -> Mapping[str, Any]:
        # TODO support exclude fields
        # exclude = (
        #     "attributes.uid",
        #     "attributes.name",
        #     "attributes.display_value",
        #     "attributes.mapping",
        #     "attributes.attribute_type",
        # )
        model = ItemModelFactory().create(item.schema)
        data = model().dump(item)

        assert isinstance(data, Mapping)
        return data
