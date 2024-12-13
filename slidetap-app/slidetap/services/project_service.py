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

from slidetap.database import DatabaseProject
from slidetap.model import Project
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService


class ProjectService:
    def __init__(
        self,
        attribute_service: AttributeService,
        database_service: DatabaseService,
    ):
        self._attribute_service = attribute_service
        self._database_service = database_service

    def get(self, uid: UUID) -> Project:
        project = self._database_service.get_project(uid)
        return project.model

    def get_optional(self, uid: UUID) -> Optional[Project]:
        project = self._database_service.get_optional_project(uid)
        if project is None:
            return None
        return project.model

    def get_all(self) -> Iterable[Project]:
        return (project.model for project in self._database_service.get_all_projects())

    def update(self, project: Project):
        database_project = self._database_service.get_project(project.uid)
        database_project.name = project.name
        self._attribute_service.create_for_project(project, project.attributes)

    def item_count(
        self, uid: UUID, item_schema_uid: UUID, selected: Optional[bool]
    ) -> Optional[int]:
        project = self.get(uid)
        if project is None:
            return None
        return self._database_service.get_project_item_count(
            uid, item_schema_uid, selected=selected
        )

    def delete(self, uid: UUID) -> bool:
        project = self._database_service.get_project(uid)
        project.delete_project()
        return True

    def set_as_search_complete(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Project:
        project = self._database_service.get_project(project)
        project.set_as_search_complete()
        return project.model

    def set_as_export_complete(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Project:
        project = self._database_service.get_project(project)
        project.set_as_export_complete()
        return project.model

    def set_as_post_processed(
        self, project: Union[UUID, Project, DatabaseProject], force: bool = False
    ) -> Project:
        project = self._database_service.get_project(project)
        project.set_as_post_processed(force=force)
        return project.model

    def set_as_post_processing(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Project:
        project = self._database_service.get_project(project)
        project.set_as_post_processing()
        return project.model

    def set_as_exporting(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Project:
        project = self._database_service.get_project(project)
        project.set_as_exporting()
        return project.model
