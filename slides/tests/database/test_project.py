import pytest

from slides.database.project import Project, ProjectStatus


@pytest.mark.unittest
class TestSlidesDatabaseProject:
    def test_project_status_initialized(self, project: Project):
        # Arrange

        # Act
        project.status = ProjectStatus.INITIALIZED

        # Assert
        assert project.initialized
        assert not project.started

    def test_project_status_started(self, project: Project):
        # Arrange

        # Act
        project.status = ProjectStatus.STARTED

        # Assert
        assert project.started
        assert not project.initialized

    def test_project_status_completed(self, project: Project):
        # Arrange

        # Act
        project.status = ProjectStatus.COMPLETED

        # Assert
        assert project.completed
        assert not project.started

    def test_project_status_failed(self, project: Project):
        # Arrange

        # Act
        project.status = ProjectStatus.FAILED

        # Assert
        assert project.failed
        assert not project.completed

    def test_get_project(self, project: Project):
        # Arrange

        # Act
        get_project = Project.get_project(project.uid)

        # Assert
        assert get_project == project

    @pytest.mark.parametrize(
        "status, expected_result",
        [
            (ProjectStatus.STARTED, False),
            (ProjectStatus.INITIALIZED, True),
        ],
    )
    def test_delete_project(
        self, project: Project, status: ProjectStatus, expected_result: bool
    ):
        # Arrange
        project.status = status

        # Act
        project.delete_project()

        # Assert
        assert project.deleted == expected_result
