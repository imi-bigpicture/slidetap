from typing import Union
from uuid import UUID, uuid4

from werkzeug.datastructures import FileStorage

from slides.database.project import Project
from slides.database.schema.schema import Schema
from slides.importer.metadata.metadata_importer import MetadataImporter


class DummyMetadataImporter(MetadataImporter):
    def search(self, user: str, project: Project, file: Union[FileStorage, bytes]):
        pass

    def schema(self) -> Schema:
        return Schema(uuid4(), "test schema")
