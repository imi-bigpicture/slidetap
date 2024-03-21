"""Metaclass for metadata exporter."""

from abc import ABCMeta, abstractmethod

from slidetap.database import Item, Project
from slidetap.exporter.exporter import Exporter


class MetadataExporter(Exporter, metaclass=ABCMeta):
    """Metaclass for metadata exporter."""

    @abstractmethod
    def export(self, project: Project):
        """Should export the metadata in project to storage."""
        raise NotImplementedError()

    @abstractmethod
    def preview_item(self, item: Item) -> str:
        """Should return a preview of the item."""
        raise NotImplementedError()
