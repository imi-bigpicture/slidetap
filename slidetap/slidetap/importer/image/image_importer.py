from abc import ABCMeta, abstractmethod

from slidetap.database.project import Project
from slidetap.importer.importer import Importer
from slidetap.model import Session


class ImageImporter(Importer, metaclass=ABCMeta):
    """Metaclass for image importer."""

    @abstractmethod
    def download(self, session: Session, project: Project):
        """Should download images matching images defined in project.

        Parameters
        ----------
        session: Session
            User session for request.
        project: Project
            Project to start.

        """
        raise NotImplementedError()
