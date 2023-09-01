"""Metaclass for metadata importer."""
from abc import ABCMeta, abstractmethod
from typing import Union

from slides.model import Session
from slides.database.project import Project
from slides.database.schema.schema import Schema
from slides.importer.importer import Importer
from werkzeug.datastructures import FileStorage


class MetadataImporter(Importer, metaclass=ABCMeta):
    """Metaclass for metadata importer."""

    @property
    @abstractmethod
    def schema(self) -> Schema:
        """Should return the schema used for returned metadata."""
        raise NotImplementedError()

    @abstractmethod
    def search(
        self, session: Session, project: Project, file: Union[FileStorage, bytes]
    ):
        """Should search for metadata based on search criteria defined in
        file, and add found metadata to project."""
        raise NotImplementedError()
