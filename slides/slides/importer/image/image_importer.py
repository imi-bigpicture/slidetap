from abc import ABCMeta, abstractmethod

from slides.database.project import Project
from slides.importer.importer import Importer
from slides.model import Session


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

    @abstractmethod
    def search(self, session: Session, project: Project):
        """Should search for images matching samples defined project.

        Parameters
        ----------
        session: Session
            User session for request.
        project: Project
            Project to start search.

        """
        raise NotImplementedError()
