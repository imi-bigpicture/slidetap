"""Metaclass for metadata exporter."""
from abc import ABCMeta, abstractmethod

from slides.database.project import Project
from slides.exporter.exporter import Exporter


class MetadataExporter(Exporter, metaclass=ABCMeta):
    """Metaclass for metadata exporter."""

    @abstractmethod
    def export(self, project: Project):
        """Should export the metadata in project to storage."""
        raise NotImplementedError()
