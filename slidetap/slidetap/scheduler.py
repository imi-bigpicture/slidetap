from typing import Any, Callable, Dict, Optional

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, current_app
from flask_apscheduler import APScheduler

from slidetap.database import db
from slidetap.flask_extension import FlaskExtension


class Scheduler(FlaskExtension):
    """Scheduler that runs jobs in background threads."""

    def __init__(
        self,
        app: Optional[Flask] = None,
    ):
        executors = {"default": ThreadPoolExecutor()}
        scheduler = BackgroundScheduler(executors=executors)
        self._scheduler = APScheduler(scheduler=scheduler)
        self._inited = False
        super().__init__(app)

    def init_app(self, app: Flask):
        """Setup scheduler."""

        if not self._inited:
            if self._scheduler.running:
                self._scheduler.shutdown()
            self._scheduler.init_app(app)
            self._scheduler.start()
            self._inited = True
        self._app = app
        super().init_app(app)

    def app_context(self):
        return self._app.app_context()

    def pause(self):
        self._scheduler.pause()

    def resume(self):
        self._scheduler.resume()

    def get_jobs(self):
        return self._scheduler.get_jobs()

    def add_job(
        self,
        id: str,
        function: Callable[..., None],
        job_parameters: Dict[str, Any],
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
            f"Adding job for {id} for function {function} and parameters {job_parameters}."
        )
        return self._scheduler.add_job(
            func=self._run_job,
            trigger=None,
            misfire_grace_time=None,
            coalesce=False,
            id=id,
            kwargs={"function": function, **job_parameters},
        )

    def _run_job(self, function: Callable[..., None], **kwargs):
        """Run the job with given parameters in the app context."""
        with self.app_context():
            with db.session.no_autoflush:
                function(**kwargs)
