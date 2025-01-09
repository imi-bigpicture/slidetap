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
from slidetap.database.project import DatabaseProject, ProjectStatus


@pytest.mark.unittest
class TestSlideTapDatabaseProject:
    def test_project_status_initialized(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.INITIALIZED

        # Assert
        assert project.initialized

    def test_project_status_searching(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.METADATA_SEARCHING

        # Assert
        assert project.metadata_searching

    def test_project_status_searched(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.METADATA_SEARCH_COMPLETE

        # Assert
        assert project.metadata_search_complete

    def test_project_status_image_pre_processing(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.IMAGE_PRE_PROCESSING

        # Assert
        assert project.image_pre_processing

    def test_project_status_image_pre_processed(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE

        # Assert
        assert project.image_pre_processing_complete

    def test_project_status_image_post_processing(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.IMAGE_POST_PROCESSING

        # Assert
        assert project.image_post_processing

    def test_project_status_image_post_processed(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE

        # Assert
        assert project.image_post_processing_complete

    def test_project_status_exporting(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.EXPORTING

        # Assert
        assert project.exporting

    def test_project_status_exported(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.EXPORT_COMPLETE

        # Assert
        assert project.export_complete

    def test_project_status_failed(self, project: DatabaseProject):
        # Arrange

        # Act
        project.status = ProjectStatus.FAILED

        # Assert
        assert project.failed
