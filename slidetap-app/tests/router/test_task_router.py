#    Copyright 2026 SECTRA AB
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

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.model import TaskCounts, TaskJob, TaskJobStatus
from slidetap.web.routers import task_router
from slidetap.web.services import LoginService, TaskQueueService
from slidetap.web.services.task_queue_service import DEFAULT_JOB_LIMIT, MAX_JOB_LIMIT


@pytest.fixture()
def task_queue_service(decoy: Decoy):
    return decoy.mock(cls=TaskQueueService)


@pytest.fixture()
def test_client(
    decoy: Decoy, simple_app: FastAPI, task_queue_service: TaskQueueService
):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: task_queue_service, provides=TaskQueueService)
    container = make_async_container(service_provider)
    simple_app.include_router(task_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.fixture()
def task_job() -> TaskJob:
    return TaskJob(
        id=1,
        task_name="slidetap.task.process_image",
        queue="image",
        status=TaskJobStatus.FAILED,
        priority=0,
        attempts=1,
        scheduled_at=None,
        deferred_at=datetime.datetime(2026, 1, 1),
        args={"image_uid": "uid"},
        lock=None,
        worker_id=None,
        abort_requested=False,
    )


@pytest.fixture()
def task_counts() -> TaskCounts:
    return TaskCounts(
        name="image",
        jobs_count=3,
        todo=1,
        doing=0,
        succeeded=1,
        failed=1,
        cancelled=0,
        aborted=0,
    )


@pytest.mark.unittest
class TestSlideTapTaskRouter:
    def test_jobs_are_got_with_the_default_limit_and_no_filters(
        self,
        decoy: Decoy,
        test_client: TestClient,
        task_queue_service: TaskQueueService,
        task_job: TaskJob,
    ):
        # Arrange
        decoy.when(
            task_queue_service.get_jobs(
                status=None, task=None, queue=None, limit=DEFAULT_JOB_LIMIT
            )
        ).then_return([task_job])

        # Act
        response = test_client.get("api/tasks/jobs")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == [task_job.model_dump(mode="json", by_alias=True)]

    def test_jobs_are_got_with_the_filters_given(
        self,
        decoy: Decoy,
        test_client: TestClient,
        task_queue_service: TaskQueueService,
        task_job: TaskJob,
    ):
        # Arrange
        decoy.when(
            task_queue_service.get_jobs(
                status=TaskJobStatus.FAILED,
                task=task_job.task_name,
                queue=task_job.queue,
                limit=5,
            )
        ).then_return([task_job])

        # Act
        response = test_client.get(
            "api/tasks/jobs",
            params={
                "status": "failed",
                "task": task_job.task_name,
                "queue": task_job.queue,
                "limit": 5,
            },
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert [job["id"] for job in response.json()] == [task_job.id]

    @pytest.mark.parametrize("limit", [0, MAX_JOB_LIMIT + 1])
    def test_jobs_with_a_limit_out_of_range_are_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        task_queue_service: TaskQueueService,
        limit: int,
    ):
        # Act
        response = test_client.get("api/tasks/jobs", params={"limit": limit})

        # Assert
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        decoy.verify(
            task_queue_service.get_jobs(
                status=Anything(), task=Anything(), queue=Anything(), limit=Anything()
            ),
            times=0,
        )

    def test_task_counts_are_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        task_queue_service: TaskQueueService,
        task_counts: TaskCounts,
    ):
        # Arrange
        decoy.when(task_queue_service.get_task_counts()).then_return([task_counts])

        # Act
        response = test_client.get("api/tasks/tasks")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == [task_counts.model_dump(mode="json", by_alias=True)]

    def test_queue_counts_are_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        task_queue_service: TaskQueueService,
        task_counts: TaskCounts,
    ):
        # Arrange
        decoy.when(task_queue_service.get_queue_counts()).then_return([task_counts])

        # Act
        response = test_client.get("api/tasks/queues")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == [task_counts.model_dump(mode="json", by_alias=True)]
