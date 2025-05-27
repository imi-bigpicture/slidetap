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

import logging
from typing import Iterable, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import DatabaseMapper, DatabaseProject
from slidetap.database.mapper import DatabaseMapperGroup
from slidetap.model import Mapper, Project, ProjectStatus
from slidetap.services import AttributeService
from slidetap.services.batch_service import BatchService
from slidetap.services.database_service import DatabaseService
from slidetap.services.mapper_service import MapperService
from slidetap.services.schema_service import SchemaService
from slidetap.services.storage_service import StorageService
from slidetap.services.validation_service import ValidationService


class ProjectService:
    def __init__(
        self,
        attribute_service: AttributeService,
        batch_service: BatchService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        mapper_service: MapperService,
        database_service: DatabaseService,
        storage_service: StorageService,
    ):
        self._attribute_service = attribute_service
        self._batch_service = batch_service
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._mapper_service = mapper_service
        self._database_service = database_service
        self._storage_service = storage_service

    def create(
        self,
        project: Project,
        session: Optional[Session] = None,
    ) -> Project:
        with self._database_service.get_session(session) as session:
            existing = self._database_service.get_optional_project(session, project)
            if existing:
                return existing.model
            database_project = self._database_service.add_project(session, project)
            self._attribute_service.create_for_project(
                database_project, project.attributes, session=session
            )
            mappers = [
                mapper
                for group in database_project.mapper_groups
                for mapper in group.mappers
            ]

            self._mapper_service.apply_mappers_to_project(
                database_project, self._schema_service.project, mappers, validate=False
            )
            self._validation_service.validate_project_attributes(
                database_project, session=session
            )

            session.commit()
            logging.info(
                f"Project {database_project.uid} created with mapping groups {database_project.mapper_groups} and mappers {[mapper for group in database_project.mapper_groups for mapper in group.mappers]}."
            )
            return database_project.model

    def get(self, uid: UUID) -> Project:
        with self._database_service.get_session() as session:
            project = self._database_service.get_project(session, uid)
            return project.model

    def get_optional(self, uid: UUID) -> Optional[Project]:
        with self._database_service.get_session() as session:
            project = self._database_service.get_optional_project(session, uid)
            if project is None:
                return None
            return project.model

    def get_all(self, root_schema_uid: Optional[UUID] = None) -> Iterable[Project]:
        with self._database_service.get_session() as session:
            projects = self._database_service.get_all_projects(session, root_schema_uid)
            return [project.model for project in projects]

    def get_all_of_root_schema(self):
        return self.get_all(self._schema_service.root.uid)

    def update(self, project: Project) -> Optional[Project]:
        with self._database_service.get_session() as session:
            database_project = self._database_service.get_optional_project(
                session, project.uid
            )
            if database_project is None:
                return None
            database_project.name = project.name
            self._attribute_service.create_for_project(
                project, project.attributes, session=session
            )
            session.commit()
            return database_project.model

    def delete(self, uid: UUID) -> Optional[bool]:
        with self._database_service.get_session() as session:
            project = self._database_service.get_optional_project(session, uid)
            if project is None:
                return None
            for batch in project.batches:
                # self._batch_service.delete(batch.uid)
                for item_schema in self._schema_service.items:
                    self._database_service.delete_items(session, batch, item_schema)
                session.delete(batch)
            session.delete(project)
            session.commit()
        self._storage_service.cleanup_project(project.model)
        return True

    def set_as_in_progress(
        self,
        project: Union[UUID, Project, DatabaseProject],
        session: Optional[Session] = None,
    ) -> Project:
        with self._database_service.get_session(session) as session:
            project = self._database_service.get_project(session, project)
            if project.status != ProjectStatus.IN_PROGRESS:
                project.status = ProjectStatus.IN_PROGRESS
                session.commit()
            logging.info(f"Project {project.uid} set as in progress.")
            return project.model

    def set_as_export_complete(
        self,
        project: Union[UUID, Project, DatabaseProject],
        session: Optional[Session] = None,
    ) -> Project:
        with self._database_service.get_session(session) as session:
            project = self._database_service.get_project(session, project)
            if project.status != ProjectStatus.EXPORTING:
                error = f"Can only set {ProjectStatus.EXPORTING} project as {ProjectStatus.EXPORT_COMPLETE}, was {project.status}"
                raise Exception(error)
            project.status = ProjectStatus.EXPORT_COMPLETE
            logging.info(f"Project {project.uid} set as export complete.")
            session.commit()
            return project.model

    def set_as_exporting(
        self,
        project: Union[UUID, Project, DatabaseProject],
        session: Optional[Session] = None,
    ) -> Project:
        with self._database_service.get_session(session) as session:
            project = self._database_service.get_project(session, project)
            if not project.completed:
                error = f"Can only set {ProjectStatus.COMPLETED} project as {ProjectStatus.EXPORTING}, was {project.status}"
                raise Exception(error)
            project.status = ProjectStatus.EXPORTING
            logging.info(f"Project {project.uid} set as exporting.")
            session.commit()
            return project.model

    def set_as_complete(
        self,
        project: Union[UUID, Project, DatabaseProject],
        session: Optional[Session] = None,
    ) -> Project:
        with self._database_service.get_session(session) as session:
            project = self._database_service.get_project(session, project)
            if not project.in_progress:
                error = f"Can only set {ProjectStatus.IN_PROGRESS} project as {ProjectStatus.COMPLETED}, was {project.status}"
                raise Exception(error)
            project.status = ProjectStatus.COMPLETED
            logging.info(f"Project {project.uid} set as complete.")
            session.commit()
            return project.model

    def lock(
        self,
        project: Union[UUID, Project, DatabaseProject],
        session: Optional[Session] = None,
    ) -> Project:
        with self._database_service.get_session(session) as session:
            project = self._database_service.get_project(session, project)
            project.locked = True
            items = self._database_service.get_items(session, project.uid)
            for item in items:
                item.locked = True
                for attribute in item.attributes.values():
                    attribute.locked = True
            session.commit()
            return project.model
