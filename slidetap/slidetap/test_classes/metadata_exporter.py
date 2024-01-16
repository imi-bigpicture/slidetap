from slidetap.database.project import Item, Project
from slidetap.exporter.metadata import MetadataExporter


class DummyMetadataExporter(MetadataExporter):
    def export(self, project: Project):
        pass

    def preview_item(self, item: Item):
        return f"Item {item.uid}"
