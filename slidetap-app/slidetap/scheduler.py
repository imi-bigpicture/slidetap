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

from enum import Enum
from typing import Any, Callable, Dict

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app


class Queue(Enum):
    """Priority queue for the scheduler."""

    DEFAULT = "default"
    HIGH = "high"


class Scheduler:
    """Scheduler that runs jobs in background threads."""

    def __init__(self, default_queue_workers: int, high_queue_workers: int):
        self._scheduler = BackgroundScheduler(
            executors={
                Queue.DEFAULT.value: ThreadPoolExecutor(default_queue_workers),
                Queue.HIGH.value: ThreadPoolExecutor(high_queue_workers),
            },
        )
        self._scheduler.start()

    def pause(self):
        self._scheduler.pause()

    def resume(self):
        self._scheduler.resume()

    def start(self):
        self._scheduler.start()

    def shutdown(self):
        self._scheduler.shutdown()

    @property
    def running(self):
        return self._scheduler.running

    def get_jobs(self):
        return self._scheduler.get_jobs()

    def add_job(
        self,
        id: str,
        function: Callable[..., None],
        job_parameters: Dict[str, Any],
        queue: Queue = Queue.DEFAULT,
    ) -> Job:
        """Add a job for the scheduler to run. Note that jobs will not run in the
        default Flask application context, so `with self._app.app_context():` is needed
        in the job function e.g. in order to access the database.

        Parameters
        ----------
        id: str
            Identifier for the job to run.
        function: Callable[..., None]
            The function to run.
        job_parameters: Iterable[Any]
            The parameters to pass to the function.
        queue: Queue
            The priority queue to run the job in.

        Returns
        ----------
        Job
            The created job.
        """
        current_app.logger.debug(
            f"Adding job {id} to queue {queue.value}, {self._scheduler.running}"
        )
        return self._scheduler.add_job(
            func=function,
            trigger=None,
            misfire_grace_time=None,
            coalesce=False,
            id=id,
            kwargs={**job_parameters},
            executor=queue.value,
        )
