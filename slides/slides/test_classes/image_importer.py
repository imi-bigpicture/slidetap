from flask import Flask

from slides.database.project import Project
from slides.importer.image import ImageImporter


class DummyImageImporter(ImageImporter):
    def download(self, user: str, project: Project):
        pass

    def search(self, user: str, project: Project):
        pass
