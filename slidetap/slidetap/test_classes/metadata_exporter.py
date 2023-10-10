from slidetap.database.project import Project
from slidetap.exporter.metadata import MetadataExporter


class DummyMetadataExporter(MetadataExporter):
    def export(self, project: Project):
        pass
