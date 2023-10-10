"""Metaclass for metadata exporter."""
from abc import ABCMeta, abstractmethod

from slidetap.database.project import Project
from slidetap.exporter.exporter import Exporter


class MetadataExporter(Exporter, metaclass=ABCMeta):
    """Metaclass for metadata exporter."""

    @abstractmethod
    def export(self, project: Project):
        """Should export the metadata in project to storage."""
        raise NotImplementedError()
