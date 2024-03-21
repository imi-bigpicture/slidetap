"""Metaclass for metadata importer."""

from abc import ABCMeta, abstractmethod
from typing import Union

from werkzeug.datastructures import FileStorage

from slidetap.database import Project, Schema
from slidetap.importer.importer import Importer
from slidetap.model import Session


class MetadataImporter(Importer, metaclass=ABCMeta):
    """Metaclass for metadata importer."""

    @property
    @abstractmethod
    def schema(self) -> Schema:
        """Should return the schema used for returned metadata."""
        raise NotImplementedError()

    @abstractmethod
    def create_project(self, session: Session, name: str) -> Project:
        """Should create a new project and return it."""
        raise NotImplementedError()

    @abstractmethod
    def search(
        self, session: Session, project: Project, file: Union[FileStorage, bytes]
    ):
        """Should search for metadata based on search criteria defined in
        file, and add found metadata to project."""
        raise NotImplementedError()
