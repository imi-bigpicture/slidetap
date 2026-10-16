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


import datetime
from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.model import (
    AttributeMigrationIssue,
    MigrationStatus,
    NotAllowedActionError,
    NotFoundError,
    Project,
    ProjectActions,
    ProjectMigration,
    ProjectStatus,
    StringAttribute,
)
from slidetap.services import ItemService, MigrationService
from slidetap.services.project_service import ProjectService
from slidetap.task import Scheduler
from slidetap.web import SlideTapWebAppFactory
from slidetap.web.routers import project_router
from slidetap.web.services import ImagePipelineService, MetadataExportService
from slidetap.web.services.login_service import LoginService

RESOLVED_AT = datetime.datetime(2026, 1, 2)


def _migration(project: Project, status: MigrationStatus) -> ProjectMigration:
    return ProjectMigration(
        project_uid=project.uid,
        source_root_schema_uid=project.root_schema_uid,
        target_root_schema_uid=uuid4(),
        previous_project_status=ProjectStatus.IN_PROGRESS,
        status=status,
        created=datetime.datetime(2026, 1, 1),
        updated=datetime.datetime(2026, 1, 1),
    )


@pytest.fixture()
def login_service(decoy: Decoy):
    return decoy.mock(cls=LoginService)


@pytest.fixture()
def project_service(decoy: Decoy):
    return decoy.mock(cls=ProjectService)


@pytest.fixture()
def migration_service(decoy: Decoy):
    return decoy.mock(cls=MigrationService)


@pytest.fixture()
def scheduler(decoy: Decoy):
    return decoy.mock(cls=Scheduler)


@pytest.fixture()
def item_service(decoy: Decoy):
    return decoy.mock(cls=ItemService)


@pytest.fixture()
def image_pipeline_service(decoy: Decoy):
    return decoy.mock(cls=ImagePipelineService)


@pytest.fixture()
def metadata_export_service(decoy: Decoy):
    return decoy.mock(cls=MetadataExportService)


@pytest.fixture()
def project_router_app(
    simple_app: FastAPI,
    login_service: LoginService,
    project_service: ProjectService,
    migration_service: MigrationService,
    scheduler: Scheduler,
    item_service: ItemService,
    image_pipeline_service: ImagePipelineService,
    metadata_export_service: MetadataExportService,
):
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: project_service, provides=ProjectService)
    service_provider.provide(lambda: migration_service, provides=MigrationService)
    service_provider.provide(lambda: scheduler, provides=Scheduler)
    service_provider.provide(lambda: item_service, provides=ItemService)
    service_provider.provide(
        lambda: image_pipeline_service, provides=ImagePipelineService
    )
    service_provider.provide(
        lambda: metadata_export_service, provides=MetadataExportService
    )

    container = make_async_container(service_provider)
    simple_app.include_router(project_router, tags=["project"])
    simple_app.add_exception_handler(NotFoundError, SlideTapWebAppFactory._not_found)
    setup_dishka(container, simple_app)
    yield simple_app


@pytest.fixture()
def test_client(project_router_app: FastAPI):
    with TestClient(project_router_app) as client:
        yield client


@pytest.mark.unittest
class TestSlideTapProjectRouter:
    def test_update_project_with_a_body_for_another_project_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        path_uid = uuid4()

        # Act
        response = test_client.post(
            f"api/projects/project/{path_uid}",
            json=project.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(project_service.update(Anything()), times=0)

    def test_update_project_with_a_body_for_the_project_is_saved(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        decoy.when(project_service.update(Anything())).then_return(project)

        # Act
        response = test_client.post(
            f"api/projects/project/{project.uid}",
            json=project.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_delete_project_not_found(
        self, decoy: Decoy, test_client: TestClient, project_service: ProjectService
    ):
        # Arrange
        uid = uuid4()
        decoy.when(project_service.get_optional(uid)).then_return(None)

        # Act
        response = test_client.delete(f"api/projects/project/{uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_project_being_exported_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        decoy.when(project_service.get_optional(project.uid)).then_return(project)
        decoy.when(project_service.set_as_deleting(project.uid)).then_raise(
            NotAllowedActionError("Cannot delete project while it is exporting")
        )

        # Act
        response = test_client.delete(f"api/projects/project/{project.uid}")

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT
        assert "exporting" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_project_is_scheduled(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        scheduler: Scheduler,
        project: Project,
    ):
        # Arrange
        deleting = project.model_copy(update={"status": ProjectStatus.DELETING})
        decoy.when(project_service.get_optional(project.uid)).then_return(project)
        decoy.when(project_service.set_as_deleting(project.uid)).then_return(deleting)

        # Act
        response = test_client.delete(f"api/projects/project/{project.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "scheduled"}
        decoy.verify(await scheduler.delete_project(deleting), times=1)

    def test_export_of_a_project_not_wholly_stored_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        decoy.when(project_service.get_exportable(project.uid)).then_raise(
            NotAllowedActionError("2 selected images are not stored")
        )

        # Act
        response = test_client.post(f"api/projects/project/{project.uid}/export")

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT
        assert "not stored" in response.json()["detail"]

    def test_the_actions_of_a_project_that_is_not_there_are_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
    ):
        # Arrange
        uid = uuid4()
        decoy.when(project_service.get_actions(uid)).then_raise(
            NotFoundError(f"Project {uid} not found")
        )

        # Act
        response = test_client.get(f"api/projects/project/{uid}/actions")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_the_projects_of_every_root_are_listed(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        on_other_root = project.model_copy(
            update={"uid": uuid4(), "root_schema_uid": uuid4()}
        )
        decoy.when(project_service.get_all()).then_return([project, on_other_root])

        # Act
        response = test_client.get("api/projects")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert [listed["rootSchemaUid"] for listed in response.json()] == [
            str(project.root_schema_uid),
            str(on_other_root.root_schema_uid),
        ]

    def test_a_project_without_a_migration_has_none_to_get(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
    ):
        # Arrange
        uid = uuid4()
        decoy.when(migration_service.get(uid)).then_raise(NotFoundError("no migration"))

        # Act
        response = test_client.get(f"api/projects/project/{uid}/migration")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_the_migration_of_a_project_is_got_with_its_plan(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        project: Project,
    ):
        # Arrange
        migration = _migration(project, MigrationStatus.CURATING)
        decoy.when(migration_service.get(project.uid)).then_return(migration)

        # Act
        response = test_client.get(f"api/projects/project/{project.uid}/migration")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert ProjectMigration.model_validate(response.json()) == migration
        assert response.json()["status"] == MigrationStatus.CURATING.value
        assert response.json()["previousProjectStatus"] == (
            ProjectStatus.IN_PROGRESS.value
        )

    @pytest.mark.asyncio
    async def test_creating_a_migration_plans_it_in_a_task(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        scheduler: Scheduler,
        project: Project,
    ):
        # Arrange
        decoy.when(migration_service.create(project.uid)).then_return(
            _migration(project, MigrationStatus.PLANNING)
        )

        # Act
        response = test_client.post(f"api/projects/project/{project.uid}/migration")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["status"] == MigrationStatus.PLANNING.value
        decoy.verify(await scheduler.plan_migration(project.uid), times=1)
        decoy.verify(migration_service.revert(project.uid), times=0)

    @pytest.mark.asyncio
    async def test_a_migration_not_planned_is_reverted(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        scheduler: Scheduler,
        project: Project,
    ):
        """Nothing would ever plan it, and the project would stay migrating."""
        # Arrange
        decoy.when(migration_service.create(project.uid)).then_return(
            _migration(project, MigrationStatus.PLANNING)
        )
        decoy.when(await scheduler.plan_migration(project.uid)).then_raise(
            RuntimeError("no queue")
        )

        # Act
        response = test_client.post(f"api/projects/project/{project.uid}/migration")

        # Assert
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        decoy.verify(migration_service.revert(project.uid), times=1)

    @pytest.mark.asyncio
    async def test_creating_a_migration_that_is_refused_is_a_conflict(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        scheduler: Scheduler,
        project: Project,
    ):
        # Arrange
        decoy.when(migration_service.create(project.uid)).then_raise(
            NotAllowedActionError("exported")
        )

        # Act
        response = test_client.post(f"api/projects/project/{project.uid}/migration")

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT
        decoy.verify(await scheduler.plan_migration(project.uid), times=0)

    @pytest.mark.parametrize("refused", [False, True])
    def test_an_attribute_issue_is_resolved(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        project: Project,
        refused: bool,
    ):
        # Arrange
        issue_uid = uuid4()
        attribute = StringAttribute(
            uid=uuid4(), schema_uid=uuid4(), updated_value="value"
        )
        resolved = AttributeMigrationIssue(
            uid=issue_uid,
            target_attribute_schema_uid=attribute.schema_uid,
            original=attribute,
            problem="problem",
            resolved_at=RESOLVED_AT,
            resolved=attribute,
        )
        when = decoy.when(migration_service.resolve(project.uid, issue_uid, attribute))
        if refused:
            when.then_raise(NotAllowedActionError("not curating"))
        else:
            when.then_return(resolved)

        # Act
        response = test_client.put(
            f"api/projects/project/{project.uid}/migration/attribute-issues/{issue_uid}",
            json=attribute.model_dump(mode="json", by_alias=True),
        )

        # Assert
        if refused:
            assert response.status_code == HTTPStatus.CONFLICT
        else:
            assert response.status_code == HTTPStatus.OK
            assert AttributeMigrationIssue.model_validate(response.json()) == resolved

    @pytest.mark.parametrize(
        "body",
        [{"content": "null", "headers": {"Content-Type": "application/json"}}, {}],
    )
    def test_an_attribute_issue_is_left_empty(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        project: Project,
        body: dict[str, Any],
    ):
        """With a null body, and with none."""
        # Arrange
        issue_uid = uuid4()
        attribute = StringAttribute(uid=uuid4(), schema_uid=uuid4())
        decoy.when(migration_service.resolve(project.uid, issue_uid, None)).then_return(
            AttributeMigrationIssue(
                uid=issue_uid,
                target_attribute_schema_uid=attribute.schema_uid,
                original=attribute,
                problem="problem",
                resolved_at=RESOLVED_AT,
            )
        )

        # Act
        response = test_client.put(
            f"api/projects/project/{project.uid}/migration/attribute-issues/{issue_uid}",
            **body,
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["resolvedAt"] is not None
        assert response.json()["resolved"] is None

    def test_a_dropped_attribute_is_accepted(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        project: Project,
    ):
        # Arrange
        issue_uid = uuid4()
        attribute = StringAttribute(
            uid=uuid4(), schema_uid=uuid4(), updated_value="value"
        )
        accepted = AttributeMigrationIssue(
            uid=issue_uid,
            original=attribute,
            problem="'value' of Tag is dropped: it has no place in Target 2.0.0.",
            resolved_at=RESOLVED_AT,
        )
        decoy.when(migration_service.resolve(project.uid, issue_uid, None)).then_return(
            accepted
        )

        # Act
        response = test_client.put(
            f"api/projects/project/{project.uid}/migration/attribute-issues/{issue_uid}",
            content="null",
            headers={"Content-Type": "application/json"},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert AttributeMigrationIssue.model_validate(response.json()) == accepted
        assert response.json()["targetAttributeSchemaUid"] is None

    @pytest.mark.parametrize("refused", [False, True])
    @pytest.mark.asyncio
    async def test_submitting_a_migration_completes_it_in_a_task(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        scheduler: Scheduler,
        project: Project,
        refused: bool,
    ):
        # Arrange
        when = decoy.when(migration_service.submit(project.uid))
        if refused:
            when.then_raise(NotAllowedActionError("not resolved"))
        else:
            when.then_return(_migration(project, MigrationStatus.COMPLETING))

        # Act
        response = test_client.post(
            f"api/projects/project/{project.uid}/migration/submit"
        )

        # Assert
        if refused:
            assert response.status_code == HTTPStatus.CONFLICT
            decoy.verify(await scheduler.complete_migration(project.uid), times=0)
        else:
            assert response.status_code == HTTPStatus.OK
            assert response.json()["status"] == MigrationStatus.COMPLETING.value
            decoy.verify(await scheduler.complete_migration(project.uid), times=1)

    @pytest.mark.asyncio
    async def test_a_migration_not_completed_is_curated_again(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        scheduler: Scheduler,
        project: Project,
    ):
        # Arrange
        decoy.when(migration_service.submit(project.uid)).then_return(
            _migration(project, MigrationStatus.COMPLETING)
        )
        decoy.when(await scheduler.complete_migration(project.uid)).then_raise(
            RuntimeError("no queue")
        )

        # Act
        response = test_client.post(
            f"api/projects/project/{project.uid}/migration/submit"
        )

        # Assert
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        decoy.verify(migration_service.resume_curating(project.uid), times=1)

    @pytest.mark.parametrize("migration_available", [True, False])
    def test_a_migration_is_reverted(
        self,
        decoy: Decoy,
        test_client: TestClient,
        migration_service: MigrationService,
        project: Project,
        migration_available: bool,
    ):
        # Arrange
        when = decoy.when(migration_service.revert(project.uid))
        if migration_available:
            when.then_return(project)
        else:
            when.then_raise(NotFoundError("no migration"))

        # Act
        response = test_client.delete(f"api/projects/project/{project.uid}/migration")

        # Assert
        assert response.status_code == (
            HTTPStatus.OK if migration_available else HTTPStatus.NOT_FOUND
        )
        if migration_available:
            assert response.json()["status"] == project.status

    def test_the_actions_of_a_project_say_whether_it_can_be_migrated(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        decoy.when(project_service.get_actions(project.uid)).then_return(
            ProjectActions(
                edit=False,
                migration_available=True,
                migrate_refusal=None,
            )
        )

        # Act
        response = test_client.get(f"api/projects/project/{project.uid}/actions")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["migrationAvailable"] is True
        assert response.json()["migrateRefusal"] is None
        assert response.json()["edit"] is False

    def test_a_project_that_is_not_completed_is_not_completed(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        project: Project,
    ):
        # Arrange
        decoy.when(project_service.get_completed(project.uid)).then_return(None)

        # Act
        response = test_client.post(f"api/projects/project/{project.uid}/complete")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"].startswith("Can only")

    @pytest.mark.parametrize(
        "action",
        [
            "repseudonymize",
            "clear_pseudonyms",
            "pseudonymize_identifiers",
            "remove_private_attributes",
            "clear_seed",
        ],
    )
    def test_a_project_that_is_not_settled_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        item_service: ItemService,
        project: Project,
        action: str,
    ):
        # Arrange
        decoy.when(project_service.get_settled(project.uid)).then_raise(
            NotAllowedActionError(
                "Only a completed, exported or failed project can be changed this "
                "way, was IN_PROGRESS."
            )
        )

        # Act
        response = test_client.post(f"api/projects/project/{project.uid}/{action}")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"].startswith("Only a completed")
        decoy.verify(item_service.repseudonymize(project.dataset_uid), times=0)
        decoy.verify(project_service.clear_seed(project.uid), times=0)

    def test_a_completed_project_is_given_new_pseudonyms(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        item_service: ItemService,
        project: Project,
    ):
        # Arrange
        completed = project.model_copy(update={"status": ProjectStatus.COMPLETED})
        decoy.when(project_service.get_settled(project.uid)).then_return(completed)
        decoy.when(item_service.repseudonymize(project.dataset_uid)).then_return(3)

        # Act
        response = test_client.post(
            f"api/projects/project/{project.uid}/repseudonymize"
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"changed": 3}

    def test_an_exportable_project_is_exported(
        self,
        decoy: Decoy,
        test_client: TestClient,
        project_service: ProjectService,
        item_service: ItemService,
        project: Project,
    ):
        # Arrange
        decoy.when(project_service.get_exportable(project.uid)).then_return(project)
        decoy.when(
            item_service.items_missing_pseudonym(project.dataset_uid)
        ).then_return(0)

        # Act
        response = test_client.post(f"api/projects/project/{project.uid}/export")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(project.uid)
