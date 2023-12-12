from uuid import UUID


from slidetap.exporter.image import ImageExporter


class DummyImageExporter(ImageExporter):
    def export(self, project_uid: UUID):
        pass
