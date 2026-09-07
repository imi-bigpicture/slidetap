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
from enum import StrEnum
from typing import Any

from slidetap.model.base_model import CamelCaseBaseModel


class TaskJobStatus(StrEnum):
    """Where a background job stands.

    The values are what the queue stores, since these are read from it and
    given back to it as a filter.
    """

    TODO = "todo"
    """Waiting for a worker."""

    DOING = "doing"
    """A worker has it."""

    SUCCEEDED = "succeeded"
    """Ran to the end."""

    FAILED = "failed"
    """Raised, and is not being tried again."""

    CANCELLED = "cancelled"
    """Taken out of the queue before a worker took it."""

    ABORTED = "aborted"
    """Stopped part-way, having been asked to."""


class TaskJob(CamelCaseBaseModel):
    """One job in the background queue."""

    id: int
    task_name: str
    queue: str
    status: TaskJobStatus
    priority: int
    attempts: int
    scheduled_at: datetime.datetime | None
    """When the job may first run, for one deferred with a delay.

    Nothing for a job deferred to run at once, which is most of them: it is not
    when the job ran, it is the time before which it must not.
    """

    args: dict[str, Any]
    """What the task was called with."""

    lock: str | None
    """No two jobs holding this run at the same time."""

    worker_id: int | None
    abort_requested: bool


class TaskCounts(CamelCaseBaseModel):
    """How many jobs of each status one task, or one queue, holds."""

    name: str
    jobs_count: int
    todo: int
    doing: int
    succeeded: int
    failed: int
    cancelled: int
    aborted: int
