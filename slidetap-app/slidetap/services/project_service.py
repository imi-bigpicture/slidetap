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

from typing import Iterable, Optional
from uuid import UUID

from slidetap.database import (
    DatabaseItem,
    DatabaseProject,
)
from slidetap.model.project import Project
from slidetap.services.attribute_service import AttributeService


class ProjectService:
    def __init__(
        self,
        attribute_service: AttributeService,
    ):
        self._attribute_service = attribute_service

    def get(self, uid: UUID) -> Project:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            raise ValueError(f"Project with uid {uid} not found")
        return project.model

    def get_optional(self, uid: UUID) -> Optional[Project]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            return None
        return project.model

    def get_all(self) -> Iterable[Project]:
        return (project.model for project in DatabaseProject.get_all_projects())

    def update(self, project: Project) -> Optional[Project]:
        database_project = DatabaseProject.get_optional(project.uid)
        if database_project is None:
            return None
        database_project.name = project.name
        self._attribute_service.create_for_project(project, project.attributes)

    def item_count(
        self, uid: UUID, item_schema_uid: UUID, selected: Optional[bool]
    ) -> Optional[int]:
        project = self.get(uid)
        if project is None:
            return None
        return DatabaseItem.get_count_for_project(uid, item_schema_uid)

    def delete(self, uid: UUID) -> Optional[bool]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            return None
        project.delete_project()
        return True

    def set_as_search_complete(self, uid: UUID) -> Optional[Project]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            return None
        project.set_as_search_complete()
        return project.model

    def set_as_export_complete(self, uid: UUID) -> Optional[Project]:
        project = DatabaseProject.get_optional(uid)
        if project is None:
            return None
        project.set_as_export_complete()
        return project.model
