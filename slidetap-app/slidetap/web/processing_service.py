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

from uuid import UUID

from flask import Flask, current_app
from werkzeug.datastructures import FileStorage

from slidetap.database import (
    DatabaseProject,
    DatabaseRootSchema,
    NotAllowedActionError,
)
from slidetap.model import ImageStatus, Project, UserSession
from slidetap.services.database_service import DatabaseService
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
        database_service: DatabaseService,
    ) -> None:
        self._image_importer = image_importer
        self._image_exporter = image_exporter
        self._metadata_importer = metadata_importer
        self._metadata_exporter = metadata_exporter
        self._project_service = project_service
        self._database_service = database_service

    def retry_image(self, session: UserSession, image_uid: UUID) -> None:
        image = self._database_service.get_image(image_uid)
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
        project = self._metadata_importer.create_project(session, project_name)
        return DatabaseProject.get_or_create_from_model(project).model

    def search_project(
        self, uid: UUID, session: UserSession, file: FileStorage
    ) -> Project:
        project = self._database_service.get_project(uid)
        self._reset_project(project)
        project.set_as_searching()
        self._metadata_importer.search(session, project.model, file)
        return project.model

    def pre_process_project(self, uid: UUID, session: UserSession) -> Project:
        project = self._database_service.get_project(uid)
        root_schema = DatabaseRootSchema.get(self._metadata_importer.schema.uid)
        for item_schema in root_schema.items:
            self._database_service.delete_project_items(
                project.uid, item_schema.uid, True
            )

        project.set_as_pre_processing()
        self._image_importer.pre_process(session, project.model)
        return project.model

    def process_project(self, uid: UUID, session: UserSession) -> Project:
        project = self._database_service.get_project(uid)
        root_schema = DatabaseRootSchema.get(self._metadata_importer.schema.uid)
        for item_schema in root_schema.items:
            self._database_service.delete_project_items(
                project.uid, item_schema.uid, True
            )
        self._image_exporter.export(project.model)
        return project.model

    def export_project(self, uid: UUID) -> Project:
        project = self._database_service.get_project(uid)
        if not project.image_post_processing_complete:
            current_app.logger.error("Can only export a post-processed project.")
            raise ValueError("Can only export a post-processed project.")
        if not project.valid:
            current_app.logger.error("Can only export a valid project.")
            raise ValueError("Can only export a valid project.")
        current_app.logger.info("Exporting project to outbox")
        self._metadata_exporter.export(project.model)
        return project.model

    def restore_project(self, uid: UUID) -> Project:
        project = self._database_service.get_project(uid)
        if project.image_post_processing:
            current_app.logger.info(f"Restoring project {uid} to pre-processed.")
            project.set_as_pre_processed(True)
            # TODO move this to image exporter
            images = self._database_service.get_project_images(uid)
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
                self._database_service.delete_project_items(
                    project.uid, item_schema.uid, False
                )
        else:
            raise NotAllowedActionError("Can only reset non-started projects")
