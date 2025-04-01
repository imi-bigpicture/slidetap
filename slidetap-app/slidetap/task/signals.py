from celery.signals import after_task_publish, celeryd_init
from flask import Flask


class SignalHandler:
    def register_signals(self, app: Flask):
        """Register all Celery signals."""

        @after_task_publish.connect
        def register_task_in_database(sender, headers, body, **kwargs):
            """Register task in database."""
            with app.app_context():
                app.logger.info(f"Task {headers.get('id')} published.")

        @celeryd_init.connect
        def on_worker_init(sender, **kwargs):
            """Initialize worker."""
            with app.app_context():
                app.logger.info("Worker initialized.")
            assert False
