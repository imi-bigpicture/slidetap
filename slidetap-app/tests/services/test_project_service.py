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


import pytest
from slidetap.model import Project
from slidetap.services.project_service import ProjectService


@pytest.mark.unittest
class TestProjectService:
    def test_get_project(self, project_service: ProjectService, project: Project):
        # Arrange
        created_project = project_service.create(project)

        # Act
        get_project = project_service.get(project.uid)

        # Assert
        assert get_project.uid == created_project.uid

    def test_delete_project(
        self,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        project_service.create(project)

        # Act
        deleted = project_service.delete(project.uid)

        # Assert
        assert deleted
