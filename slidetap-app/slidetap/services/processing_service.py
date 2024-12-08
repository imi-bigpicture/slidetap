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

from typing import Optional
from uuid import UUID

from flask import Flask, current_app
from werkzeug.datastructures import FileStorage

from slidetap.database import (
    DatabaseImage,
    DatabaseItem,
    DatabaseProject,
    NotAllowedActionError,
)
from slidetap.database.schema.root_schema import DatabaseRootSchema
from slidetap.model import UserSession
from slidetap.model.image_status import ImageStatus
from slidetap.model.project import Project
from slidetap.services.project_service import ProjectService
from slidetap.web.exporter import ImageExporter, MetadataExporter
from slidetap.web.importer import ImageImporter, MetadataImporter


class ProcessingService:
    def __init__(
        self,
        image_importer: ImageImporter,
        image_exporter: ImageExporter,
        metadata_importer: MetadataImporter,
        metadata_exporter: MetadataExporter,
        project_service: ProjectService,
    ) -> None:
        self._image_importer = image_importer
        self._image_exporter = image_exporter
        self._metadata_importer = metadata_importer
        self._metadata_exporter = metadata_exporter
        self._project_service = project_service

    def retry_image(self, session: UserSession, image_uid: UUID) -> None:
        image = DatabaseImage.get(image_uid)
        if image is None:
            return
        image.status_message = ""
        if image.status == ImageStatus.DOWNLOADING_FAILED:
            image.reset_as_not_started()
            self._image_importer.redo_image_download(session, image.model)
        elif image.status == ImageStatus.PRE_PROCESSING_FAILED:
            image.reset_as_downloaded()
            self._image_importer.redo_image_pre_processing(image.model)
        elif image.status == ImageStatus.POST_PROCESSING_FAILED:
            image.reset_as_pre_processed()
            self._image_exporter.re_export(image.model)

    def create_project(self, session: UserSession, project_name: str) -> Project:
        return self._metadata_importer.create_project(session, project_name)

    def search_project(
        self, uid: UUID, session: UserSession, file: FileStorage
    ) -> Optional[Project]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            return None
        self._reset_project(project)
        project.set_as_searching()
        self._metadata_importer.search(session, project.model, file)
        return project.model

    def pre_process_project(self, uid: UUID, session: UserSession) -> Optional[Project]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            return None
        root_schema = DatabaseRootSchema.get(self._metadata_importer.schema.uid)
        for item_schema in root_schema.items:
            DatabaseItem.delete_for_project_and_schema(
                project.uid, item_schema.uid, True
            )
        project.set_as_pre_processing()
        self._image_importer.pre_process(session, project.model)
        return project.model

    def process_project(self, uid: UUID, session: UserSession) -> Optional[Project]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            return None
        root_schema = DatabaseRootSchema.get(self._metadata_importer.schema.uid)
        for item_schema in root_schema.items:
            DatabaseItem.delete_for_project_and_schema(
                project.uid, item_schema.uid, True
            )
        self._image_exporter.export(project.model)
        return project.model

    def export_project(self, uid: UUID) -> Optional[Project]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            current_app.logger.error(f"Project {uid} not found.")
            return None
        if not project.image_post_processing_complete:
            current_app.logger.error("Can only export a post-processed project.")
            raise ValueError("Can only export a post-processed project.")
        if not project.valid:
            current_app.logger.error("Can only export a valid project.")
            raise ValueError("Can only export a valid project.")
        current_app.logger.info("Exporting project to outbox")
        self._metadata_exporter.export(project.model)
        return project.model

    def restore_project(self, uid: UUID) -> Optional[Project]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            return None
        if project.image_post_processing:
            current_app.logger.info(f"Restoring project {uid} to pre-processed.")
            project.set_as_pre_processed(True)
            # TODO move this to image exporter
            images = DatabaseImage.get_for_project(uid)
            for image in [image for image in images if image.post_processing]:
                current_app.logger.debug(
                    f"Restoring image {image.uid} to pre-processed."
                )
                image.set_as_pre_processed(True)
            current_app.logger.info(f"Restarting export of project {uid}.")
            self._image_exporter.export(project.model)
        return project.model

    def restore_all_projects(self, app: Flask) -> None:
        with app.app_context():
            for project in self._project_service.get_all():
                self.restore_project(project.uid)

    def _reset_project(self, project: DatabaseProject):
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
            self._metadata_importer.reset_project(project.model)
            self._image_importer.reset_project(project.model)
            project.reset()
            root_schema = DatabaseRootSchema.get(self._metadata_importer.schema.uid)
            for item_schema in root_schema.items:
                DatabaseItem.delete_for_project_and_schema(
                    project.uid, item_schema.uid, False
                )
        else:
            raise NotAllowedActionError("Can only reset non-started projects")
