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

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from procrastinate import App as TaskApp
from procrastinate.jobs import Job

from slidetap.model import TaskCounts, TaskJob, TaskJobStatus

DEFAULT_JOB_LIMIT = 200
"""How many jobs a listing returns when it is not told."""

MAX_JOB_LIMIT = 2000
"""As many as one listing will return, however many are asked for."""

UNFINISHED_STATUSES: Sequence[TaskJobStatus] = (
    TaskJobStatus.TODO,
    TaskJobStatus.DOING,
    TaskJobStatus.FAILED,
    TaskJobStatus.CANCELLED,
    TaskJobStatus.ABORTED,
)
"""What a listing covers when it is not asked for one status.

Every status but ``succeeded``, which is the one that grows without bound: a
queue that has been running a while holds one row per piece of work it has ever
done, and reading them to show the newest few is the whole table for a page
nobody scrolls. How many there are is what the counts are for. The rest are
bounded by what is pending or went wrong, which is what somebody opening this
page came to see.
"""


class TaskQueueService:
    """What the background queue holds, for looking at.

    Read-only. The queue is filled by the application deferring work through
    :class:`slidetap.task.Scheduler`, and a second way of reaching into it
    would be a way of starting work that nothing else knows about.

    Asked of Procrastinate's own job manager, so that what this shows follows
    its schema rather than a copy of it here.
    """

    def __init__(self, task_app: TaskApp):
        self._task_app = task_app
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def get_jobs(
        self,
        status: TaskJobStatus | None = None,
        task: str | None = None,
        queue: str | None = None,
        limit: int = DEFAULT_JOB_LIMIT,
    ) -> list[TaskJob]:
        """Get the newest jobs in the queue, filtered by what is given.

        Parameters
        ----------
        status: TaskJobStatus | None
            Only jobs in this status. Every status but ``succeeded`` when not
            given, as :data:`UNFINISHED_STATUSES` says.
        task: str | None
            Only jobs of this task, by its full name.
        queue: str | None
            Only jobs in this queue.
        limit: int
            How many to return, of the newest.

        Returns
        -------
        list[TaskJob]
            The jobs, newest first.
        """
        self._logger.debug(
            f"Listing jobs (status={status}, task={task}, queue={queue})."
        )
        statuses = (status,) if status is not None else UNFINISHED_STATUSES
        # One listing per status, since the job manager takes one at a time.
        # Together rather than in turn: they are separate queries against the
        # same pool, and each is bounded by how many jobs are in that status.
        listings = await asyncio.gather(
            *(
                self._task_app.job_manager.list_jobs_async(
                    status=status_to_list.value, task=task, queue=queue
                )
                for status_to_list in statuses
            )
        )
        # A job carries no id until it has been deferred, which none of these
        # can be short of — they were read from the queue — but the type allows
        # it, and a made-up id would be worse than leaving one out.
        jobs = [
            self._job(job, job.id, status_listed)
            for status_listed, listing in zip(statuses, listings, strict=True)
            for job in listing
            if job.id is not None
        ]
        # Newest first, by the id the queue handed out in the order jobs were
        # deferred: the listings come back oldest first, and each covers one
        # status, so neither is the order the page reads them in.
        jobs.sort(key=lambda job: job.id, reverse=True)
        return jobs[: min(limit, MAX_JOB_LIMIT)]

    async def get_task_counts(self) -> list[TaskCounts]:
        """Get every task the queue has held, with a count of each status."""
        self._logger.debug("Listing task counts.")
        return [
            self._counts(row)
            for row in await self._task_app.job_manager.list_tasks_async()
        ]

    async def get_queue_counts(self) -> list[TaskCounts]:
        """Get every queue, with a count of each status."""
        self._logger.debug("Listing queue counts.")
        return [
            self._counts(row)
            for row in await self._task_app.job_manager.list_queues_async()
        ]

    @staticmethod
    def _job(job: Job, job_id: int, status: TaskJobStatus) -> TaskJob:
        """One job, as the status it was listed under.

        The status is taken from the listing rather than from the job: it is
        what was asked for, so it needs no widening of the model to a string
        the queue might one day add.
        """
        return TaskJob(
            id=job_id,
            task_name=job.task_name,
            queue=job.queue,
            status=status,
            priority=job.priority,
            attempts=job.attempts,
            scheduled_at=job.scheduled_at,
            args=dict(job.task_kwargs),
            lock=job.lock,
            worker_id=job.worker_id,
            abort_requested=job.abort_requested,
        )

    @staticmethod
    def _counts(row: dict[str, Any]) -> TaskCounts:
        """The job manager's summary row, as a count of its own.

        Its keys are read with defaults: a status Procrastinate adds later is
        one this does not yet count, which is not a reason to fail the request.
        """
        return TaskCounts(
            name=row["name"],
            jobs_count=row.get("jobs_count", 0),
            todo=row.get("todo", 0),
            doing=row.get("doing", 0),
            succeeded=row.get("succeeded", 0),
            failed=row.get("failed", 0),
            cancelled=row.get("cancelled", 0),
            aborted=row.get("aborted", 0),
        )
