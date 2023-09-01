from slides.database.project import Project
from slides.exporter.metadata import MetadataExporter


class DummyMetadataExporter(MetadataExporter):
    def export(self, project: Project):
        pass
