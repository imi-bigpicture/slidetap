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

from typing import Iterable, Optional, Union
from uuid import UUID

from flask import current_app
from slidetap.database import DatabaseProject, db
from slidetap.model import Project, ProjectStatus
from slidetap.services.attribute_service import AttributeService
from slidetap.services.batch_service import BatchService
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class ProjectService:
    def __init__(
        self,
        attribute_service: AttributeService,
        batch_service: BatchService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
    ):
        self._attribute_service = attribute_service
        self._batch_service = batch_service
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service

    def create(self, project: Project) -> Project:
        database_project = DatabaseProject.get_or_create_from_model(
            project, self._schema_service.root.project
        )
        self._validation_service.validate_project_attributes(database_project)
        db.session.commit()
        return database_project.model

    def get(self, uid: UUID) -> Project:
        project = self._database_service.get_project(uid)
        return project.model

    def get_optional(self, uid: UUID) -> Optional[Project]:
        project = self._database_service.get_optional_project(uid)
        if project is None:
            return None
        return project.model

    def get_all(self, root_schema_uid: Optional[UUID] = None) -> Iterable[Project]:
        return (
            project.model
            for project in self._database_service.get_all_projects(root_schema_uid)
        )

    def get_all_of_root_schema(self):
        return self.get_all(self._schema_service.root.uid)

    def update(self, project: Project) -> Optional[Project]:
        database_project = self._database_service.get_optional_project(project.uid)
        if database_project is None:
            return None
        database_project.name = project.name
        self._attribute_service.create_for_project(project, project.attributes)
        return database_project.model

    def delete(self, uid: UUID) -> Optional[bool]:
        project = self._database_service.get_optional_project(uid)
        if project is None:
            return None
        for batch in project.batches:
            # self._batch_service.delete(batch.uid)
            for item_schema in self._schema_service.items:
                self._database_service.delete_items(batch, item_schema)
            db.session.delete(batch)
        db.session.delete(project)
        db.session.commit()
        return True

    def set_as_in_progress(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Project:
        project = self._database_service.get_project(project)
        if project.status != ProjectStatus.IN_PROGRESS:
            project.status = ProjectStatus.IN_PROGRESS
            db.session.commit()
        current_app.logger.debug(f"Project {project.uid} set as in progress.")
        return project.model

    def set_as_export_complete(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Project:
        project = self._database_service.get_project(project)
        if project.status != ProjectStatus.EXPORTING:
            error = f"Can only set {ProjectStatus.EXPORTING} project as {ProjectStatus.EXPORT_COMPLETE}, was {project.status}"
            raise Exception(error)
        project.status = ProjectStatus.EXPORT_COMPLETE
        current_app.logger.debug(f"Project {project.uid} set as export complete.")
        db.session.commit()
        return project.model

    def set_as_exporting(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Project:
        project = self._database_service.get_project(project)
        if not project.completed:
            error = f"Can only set {ProjectStatus.COMPLETED} project as {ProjectStatus.EXPORTING}, was {project.status}"
            raise Exception(error)
        project.status = ProjectStatus.EXPORTING
        current_app.logger.debug(f"Project {project.uid} set as exporting.")
        db.session.commit()
        return project.model

    def set_as_complete(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Project:
        project = self._database_service.get_project(project)
        if not project.in_progress:
            error = f"Can only set {ProjectStatus.IN_PROGRESS} project as {ProjectStatus.COMPLETED}, was {project.status}"
            raise Exception(error)
        project.status = ProjectStatus.COMPLETED
        current_app.logger.debug(f"Project {project.uid} set as comple.")
        db.session.commit()
        return project.model

    def lock(self, project: Union[UUID, Project, DatabaseProject]) -> Project:
        project = self._database_service.get_project(project)
        project.locked = True
        items = self._database_service.get_items(project.uid)
        for item in items:
            item.locked = True
            for attribute in item.attributes.values():
                attribute.locked = True
        db.session.commit()
        return project.model
