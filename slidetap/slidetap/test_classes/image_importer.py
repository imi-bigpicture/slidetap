from flask import Flask

from slidetap.database.project import Project
from slidetap.importer.image import ImageImporter


class DummyImageImporter(ImageImporter):
    def preprocess(self, user: str, project: Project):
        pass

    def search(self, user: str, project: Project):
        pass
