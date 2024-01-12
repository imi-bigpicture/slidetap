"""Service for accessing projects and project items."""

from typing import Optional, Sequence, Union
from uuid import UUID
from flask import current_app

from werkzeug.datastructures import FileStorage

from slidetap.database import Item, NotAllowedActionError, Project
from slidetap.exporter import ImageExporter, MetadataExporter
from slidetap.importer import ImageImporter, MetadataImporter
from slidetap.model import Session


class ProjectService:
    def __init__(
        self,
        image_importer: ImageImporter,
        image_exporter: ImageExporter,
        metadata_importer: MetadataImporter,
        metadata_exporter: MetadataExporter,
    ):
        self._image_importer = image_importer
        self._image_exporter = image_exporter
        self._metadata_importer = metadata_importer
        self._metadata_exporter = metadata_exporter

    def create(self, project_name: str):
        project = Project(project_name, self._metadata_importer.schema)
        return project

    def get(self, uid: UUID) -> Optional[Project]:
        return Project.get(uid)

    def get_all(self) -> Sequence[Project]:
        return Project.get_all_projects()

    def update(self, uid: UUID, name: str) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None
        project.name = name
        project.update()
        return project

    def upload(
        self, uid: UUID, session: Session, file: FileStorage
    ) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None

        self._reset(project)
        project.set_as_searching()
        self._metadata_importer.search(session, project, file)
        return project

    def item_count(
        self, uid: UUID, item_schema_uid: UUID, selected: Optional[bool]
    ) -> Optional[int]:
        project = self.get(uid)
        if project is None:
            return None
        return Item.get_count_for_project(uid, item_schema_uid)

    def items(
        self,
        uid: UUID,
        item_schema_uid: UUID,
        included: bool,
        excluded: bool,
    ) -> Optional[Sequence[Item]]:
        project = self.get(uid)
        if project is None:
            return None
        if included and not excluded:
            selected = True
        elif excluded and not included:
            selected = False
        else:
            selected = None
        return Item.get_for_project(uid, item_schema_uid, selected)

    def download(self, uid: UUID, session: Session) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None
        Item.delete_for_project(project.uid, True)
        project.set_as_pre_processing()
        self._image_importer.download(session, project)
        return project

    def process(self, uid: UUID, session: Session) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None
        Item.delete_for_project(project.uid, True)
        self._image_exporter.export(project)
        return project

    def export(self, uid: UUID) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return
        current_app.logger.info("Exporting project to outbox")
        self._metadata_exporter.export(project)
        return project

    def delete(self, uid: UUID) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None
        project.delete_project()
        return project

    def _reset(self, project: Project):
        """Reset a project to INITIALIZED status.

        Parameters
        ----------
        project: Project
            Project to reset. Project must not have status STARTED or above.

        """
        if (
            project.initialized
            or project.metadata_searching
            or project.metadata_search_complete
        ):
            self._metadata_importer.reset_project(project)
            self._image_importer.reset_project(project)
            project.reset()
            Item.delete_for_project(project.uid)
        else:
            raise NotAllowedActionError("Can only reset non-started projects")
