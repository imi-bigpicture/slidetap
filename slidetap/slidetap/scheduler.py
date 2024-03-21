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

    def __init__(self):
        self._scheduler = BackgroundScheduler(
            executors={
                Queue.DEFAULT.value: ThreadPoolExecutor(),
                Queue.HIGH.value: ThreadPoolExecutor(),
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
        """Add a job for the scheduler to run.

        Parameters
        ----------
        id: str
            Identifier for the job to run.
        function: Callable[..., None]
            The function to run.
        job_parameters: Iterable[Any]
            The parameters to pass to the function.

        Returns
        ----------
        Job
            The created job.
        """
        current_app.logger.info(
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
