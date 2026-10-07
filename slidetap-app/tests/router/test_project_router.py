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


from http import HTTPStatus
from uuid import uuid4

import pytest
from decoy import Decoy
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.model import NotAllowedActionError, NotFoundError, Project, ProjectStatus
from slidetap.services import ItemService
from slidetap.services.project_service import ProjectService
from slidetap.task import Scheduler
from slidetap.web import SlideTapWebAppFactory
from slidetap.web.routers import project_router
from slidetap.web.services import ImagePipelineService, MetadataExportService
from slidetap.web.services.login_service import LoginService


@pytest.fixture()
def login_service(decoy: Decoy):
    return decoy.mock(cls=LoginService)


@pytest.fixture()
def project_service(decoy: Decoy):
    return decoy.mock(cls=ProjectService)


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
def scheduler(decoy: Decoy):
    return decoy.mock(cls=Scheduler)


@pytest.fixture()
def project_router_app(
    simple_app: FastAPI,
    login_service: LoginService,
    project_service: ProjectService,
    item_service: ItemService,
    image_pipeline_service: ImagePipelineService,
    metadata_export_service: MetadataExportService,
    scheduler: Scheduler,
):
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: project_service, provides=ProjectService)
    service_provider.provide(lambda: item_service, provides=ItemService)
    service_provider.provide(
        lambda: image_pipeline_service, provides=ImagePipelineService
    )
    service_provider.provide(
        lambda: metadata_export_service, provides=MetadataExportService
    )
    service_provider.provide(lambda: scheduler, provides=Scheduler)

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
