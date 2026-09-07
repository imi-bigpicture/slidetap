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

"""FastAPI router for looking at the background task queue."""

from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query

from slidetap.model import TaskCounts, TaskJob, TaskJobStatus
from slidetap.web.services import TaskQueueService
from slidetap.web.services.login_service import require_valid_token
from slidetap.web.services.task_queue_service import DEFAULT_JOB_LIMIT, MAX_JOB_LIMIT

task_router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@task_router.get("/jobs")
async def get_jobs(
    task_queue_service: FromDishka[TaskQueueService],
    status: Annotated[TaskJobStatus | None, Query()] = None,
    task: Annotated[str | None, Query()] = None,
    queue: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_JOB_LIMIT)] = DEFAULT_JOB_LIMIT,
) -> list[TaskJob]:
    """Get the newest jobs in the queue.

    Parameters
    ----------
    status: TaskJobStatus | None
        Only jobs in this status.
    task: str | None
        Only jobs of this task, by its full name.
    queue: str | None
        Only jobs in this queue.
    limit: int
        How many to return, of the newest.

    Returns
    ----------
    list[TaskJob]
        The jobs, newest first.
    """
    return await task_queue_service.get_jobs(
        status=status, task=task, queue=queue, limit=limit
    )


@task_router.get("/tasks")
async def get_task_counts(
    task_queue_service: FromDishka[TaskQueueService],
) -> list[TaskCounts]:
    """Get every task the queue has held, with a count of each status.

    Returns
    ----------
    list[TaskCounts]
        One count per task.
    """
    return await task_queue_service.get_task_counts()


@task_router.get("/queues")
async def get_queue_counts(
    task_queue_service: FromDishka[TaskQueueService],
) -> list[TaskCounts]:
    """Get every queue, with a count of each status.

    Returns
    ----------
    list[TaskCounts]
        One count per queue.
    """
    return await task_queue_service.get_queue_counts()
