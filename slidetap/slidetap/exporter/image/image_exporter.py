"""Metaclass for metadata exporter."""

from abc import ABCMeta, abstractmethod
from slidetap.database import Project
from slidetap.exporter.exporter import Exporter


class ImageExporter(Exporter, metaclass=ABCMeta):
    @abstractmethod
    def export(self, project: Project):
        """Should export the images in project to storage."""
        raise NotImplementedError()
