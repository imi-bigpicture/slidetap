from slidetap.database import Item, Project
from slidetap.exporter import MetadataExporter


class DummyMetadataExporter(MetadataExporter):
    def export(self, project: Project):
        pass

    def preview_item(self, item: Item):
        return f"Item {item.uid}"
