#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Service for accessing projects and project items."""

from typing import Dict, Iterable, Optional
from uuid import UUID

from flask import Flask, current_app
from werkzeug.datastructures import FileStorage

from slidetap.database import Attribute, Item, NotAllowedActionError, Project, db
from slidetap.database.project import Image
from slidetap.exporter import ImageExporter, MetadataExporter
from slidetap.importer import ImageImporter, MetadataImporter
from slidetap.model import Session
from slidetap.model.validation import ProjectValidation


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

    def create(self, session: Session, project_name: str):
        return self._metadata_importer.create_project(session, project_name)

    def get(self, uid: UUID) -> Optional[Project]:
        return Project.get_optional(uid)

    def get_all(self) -> Iterable[Project]:
        return Project.get_all_projects()

    def update(
        self, uid: UUID, name: str, attributes: Dict[str, Attribute]
    ) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None
        project.name = name
        project.set_attributes(attributes)
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

    def pre_process(self, uid: UUID, session: Session) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None
        Item.delete_for_project(project.uid, True)
        project.set_as_pre_processing()
        self._image_importer.pre_process(session, project)
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
        if not project.image_post_processing_complete:
            raise ValueError("Can only export a post-processed project.")
        if not project.valid:
            raise ValueError("Can only export a valid project.")
        current_app.logger.info("Exporting project to outbox")
        self._metadata_exporter.export(project)
        return project

    def delete(self, uid: UUID) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None
        project.delete_project()
        return project

    def validate(self, uid: UUID):
        project = self.get(uid)
        if project is None:
            return None
        items = Item.get_for_project(uid)
        for item in items:
            item.validate(True, True, False)
        db.session.commit()

    def validation(self, uid: UUID) -> Optional[ProjectValidation]:
        project = self.get(uid)
        if project is None:
            return None
        return project.validation

    def restore(self, uid: UUID) -> Optional[Project]:
        project = self.get(uid)
        if project is None:
            return None
        if project.image_post_processing:
            current_app.logger.info(f"Restoring project {uid} to pre-processed.")
            project.set_as_pre_processed(True)
            # TODO move this to image exporter
            images = Image.get_for_project(uid)
            for image in [image for image in images if image.post_processing]:
                current_app.logger.info(
                    f"Restoring image {image.uid} to pre-processed."
                )
                image.set_as_pre_processed(True)
            current_app.logger.info(f"Restarting export of project {uid}.")
            self._image_exporter.export(project)
        return project

    def restore_all(self, app: Flask) -> None:
        with app.app_context():
            for project in self.get_all():
                self.restore(project.uid)

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
