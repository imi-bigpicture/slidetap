from typing import Union
from uuid import UUID, uuid4

from werkzeug.datastructures import FileStorage

from slidetap.database.project import Project
from slidetap.database.schema.schema import Schema
from slidetap.importer.metadata.metadata_importer import MetadataImporter


class DummyMetadataImporter(MetadataImporter):
    def search(self, user: str, project: Project, file: Union[FileStorage, bytes]):
        pass

    def schema(self) -> Schema:
        return Schema(uuid4(), "test schema")
