from flask import Flask

from slidetap.database.project import Project
from slidetap.importer.image import ImageImporter


class DummyImageImporter(ImageImporter):
    def download(self, user: str, project: Project):
        pass

    def search(self, user: str, project: Project):
        pass
