from slidetap.database import Project
from slidetap.importer import ImageImporter


class DummyImageImporter(ImageImporter):
    def preprocess(self, user: str, project: Project):
        pass

    def search(self, user: str, project: Project):
        pass
