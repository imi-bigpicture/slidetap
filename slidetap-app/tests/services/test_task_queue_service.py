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
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from procrastinate.jobs import Job

from slidetap.model import TaskJobStatus
from slidetap.web.services import TaskQueueService
from slidetap.web.services.task_queue_service import JOB_TIMES_QUERY

DEFERRED = datetime.datetime(2026, 10, 9, 12, 0, tzinfo=datetime.UTC)
STARTED = datetime.datetime(2026, 10, 9, 12, 5, tzinfo=datetime.UTC)
FINISHED = datetime.datetime(2026, 10, 9, 12, 30, tzinfo=datetime.UTC)


def create_job(job_id: int) -> Job:
    return Job(
        id=job_id,
        queue="default",
        lock=None,
        queueing_lock=None,
        task_name="slidetap:process_metadata_import",
        task_kwargs={"batch_uid": "abc"},
    )


def create_task_app(
    jobs_by_status: dict[str, list[Job]], time_rows: list[dict[str, Any]]
) -> MagicMock:
    """A task app whose queue holds the given jobs and events."""
    task_app = MagicMock()

    async def list_jobs_async(status: str, **_: Any) -> list[Job]:
        return jobs_by_status.get(status, [])

    task_app.job_manager.list_jobs_async = list_jobs_async
    task_app.connector.execute_query_all_async = AsyncMock(return_value=time_rows)
    return task_app


class TestJobTimes:
    @pytest.mark.asyncio
    async def test_a_finished_job_has_its_times(self):
        # Arrange
        task_app = create_task_app(
            {"failed": [create_job(1)]},
            [
                {
                    "job_id": 1,
                    "deferred_at": DEFERRED,
                    "started_at": STARTED,
                    "finished_at": FINISHED,
                }
            ],
        )
        service = TaskQueueService(task_app)

        # Act
        jobs = await service.get_jobs(status=TaskJobStatus.FAILED)

        # Assert
        assert len(jobs) == 1
        assert jobs[0].deferred_at == DEFERRED
        assert jobs[0].started_at == STARTED
        assert jobs[0].finished_at == FINISHED

    @pytest.mark.asyncio
    async def test_a_job_retried_after_it_finished_is_not_finished(self):
        # Arrange — started again after it failed, and running now.
        task_app = create_task_app(
            {"doing": [create_job(1)]},
            [
                {
                    "job_id": 1,
                    "deferred_at": DEFERRED,
                    "started_at": FINISHED + datetime.timedelta(minutes=1),
                    "finished_at": FINISHED,
                }
            ],
        )
        service = TaskQueueService(task_app)

        # Act
        jobs = await service.get_jobs(status=TaskJobStatus.DOING)

        # Assert
        assert jobs[0].started_at == FINISHED + datetime.timedelta(minutes=1)
        assert jobs[0].finished_at is None

    @pytest.mark.asyncio
    async def test_only_the_jobs_returned_are_looked_up(self):
        # Arrange
        task_app = create_task_app(
            {"todo": [create_job(1), create_job(2), create_job(3)]}, []
        )
        service = TaskQueueService(task_app)

        # Act
        await service.get_jobs(status=TaskJobStatus.TODO, limit=2)

        # Assert — newest first, so the two highest ids.
        task_app.connector.execute_query_all_async.assert_awaited_once_with(
            JOB_TIMES_QUERY, job_ids=[3, 2]
        )

    @pytest.mark.asyncio
    async def test_jobs_are_listed_without_times_when_they_cannot_be_read(self):
        # Arrange
        task_app = create_task_app({"todo": [create_job(1)]}, [])
        task_app.connector.execute_query_all_async = AsyncMock(
            side_effect=RuntimeError("no such table")
        )
        service = TaskQueueService(task_app)

        # Act
        jobs = await service.get_jobs(status=TaskJobStatus.TODO)

        # Assert
        assert [job.id for job in jobs] == [1]
        assert jobs[0].deferred_at is None
        assert jobs[0].started_at is None
        assert jobs[0].finished_at is None

    @pytest.mark.asyncio
    async def test_an_empty_queue_is_not_looked_up(self):
        # Arrange
        task_app = create_task_app({}, [])
        service = TaskQueueService(task_app)

        # Act
        jobs = await service.get_jobs(status=TaskJobStatus.TODO)

        # Assert
        assert jobs == []
        task_app.connector.execute_query_all_async.assert_not_awaited()
