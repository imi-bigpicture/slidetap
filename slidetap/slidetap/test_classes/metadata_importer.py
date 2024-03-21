from typing import Union
from uuid import uuid4

from werkzeug.datastructures import FileStorage

from slidetap.database import Project, ProjectSchema, Schema
from slidetap.importer import MetadataImporter
from slidetap.model import Session
from slidetap.scheduler import Scheduler


class DummyMetadataImporter(MetadataImporter):
    def __init__(self, scheduler: Scheduler):
        super().__init__(scheduler)
        self._schema = Schema(uuid4(), "test schema")

    def create_project(self, session: Session, name: str) -> Project:
        project_schema = ProjectSchema.get_for_schema(self.schema)
        return Project(name, project_schema)

    def search(self, user: str, project: Project, file: Union[FileStorage, bytes]):
        pass

    @property
    def schema(self) -> Schema:
        return self._schema
