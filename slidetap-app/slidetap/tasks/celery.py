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

"""Factory for creating a Celery application with Flask context tasks."""

from functools import cached_property
from logging.config import dictConfig
from typing import Literal, Optional

from celery import Celery, Task
from celery.signals import worker_process_init
from flask import Flask

from slidetap.config import Config
from slidetap.database import db, setup_db
from slidetap.tasks.processors import (
    ImagePostProcessor,
    ImagePreProcessor,
    MetadataExportProcessor,
    MetadataImportProcessor,
)
from slidetap.tasks.processors.processor_factory import ProcessorFactory


class SlideTapCeleryAppFactory:
    @classmethod
    def create_celery_worker_app(
        cls,
        image_pre_processor_factory: Optional[
            ProcessorFactory[ImagePreProcessor]
        ] = None,
        image_post_processor_factory: Optional[
            ProcessorFactory[ImagePostProcessor]
        ] = None,
        metadata_export_processor_factory: Optional[
            ProcessorFactory[MetadataExportProcessor]
        ] = None,
        metadata_import_processor_factory: Optional[
            ProcessorFactory[MetadataImportProcessor]
        ] = None,
        config: Optional[Config] = None,
    ):
        if config is None:
            config = Config()
        cls._setup_logging(config.flask_log_level)
        flask_app = cls._create_flask_app(config)
        flask_app.logger.info("Creating SlideTap Celery worker app.")
        celery_app = cls.create_celery_app(
            flask_app,
            config,
            image_pre_processor_factory,
            image_post_processor_factory,
            metadata_export_processor_factory,
            metadata_import_processor_factory,
        )
        flask_app.logger.info("SlideTap Celery worker app created.")
        return celery_app

    @classmethod
    def create_celery_app(
        cls,
        flask_app: Flask,
        config: Config,
        image_pre_processor_factory: Optional[
            ProcessorFactory[ImagePreProcessor]
        ] = None,
        image_post_processor_factory: Optional[
            ProcessorFactory[ImagePostProcessor]
        ] = None,
        metadata_export_processor_factory: Optional[
            ProcessorFactory[MetadataExportProcessor]
        ] = None,
        metadata_import_processor_factory: Optional[
            ProcessorFactory[MetadataImportProcessor]
        ] = None,
    ) -> Celery:
        """Create and configure a Celery application with Flask context tasks."""
        flask_app.logger.info("Creating Celery app.")

        class FlaskTask(Task):
            def __call__(self, *args: object, **kwargs: object) -> object:
                with flask_app.app_context():
                    return self.run(*args, **kwargs)

            @cached_property
            def image_pre_processor(self) -> ImagePreProcessor:
                if image_pre_processor_factory is None:
                    raise ValueError("Image pre-processor factory not set.")
                with flask_app.app_context():
                    return image_pre_processor_factory.create(flask_app)

            @cached_property
            def image_post_processor(self) -> ImagePostProcessor:
                if image_post_processor_factory is None:
                    raise ValueError("Image post-processor factory not set.")
                with flask_app.app_context():
                    return image_post_processor_factory.create(flask_app)

            @cached_property
            def metadata_export_processor(self) -> MetadataExportProcessor:
                if metadata_export_processor_factory is None:
                    raise ValueError("Metadata export processor factory not set.")
                with flask_app.app_context():
                    return metadata_export_processor_factory.create(flask_app)

            @cached_property
            def metadata_import_processor(self) -> MetadataImportProcessor:
                if metadata_import_processor_factory is None:
                    raise ValueError("Metadata import processor factory not set.")
                with flask_app.app_context():
                    return metadata_import_processor_factory.create(flask_app)

        celery_app = Celery(flask_app.name, task_cls=FlaskTask)
        celery_app.config_from_object(config.celery_config)
        celery_app.set_default()

        @worker_process_init.connect
        def prep_db_pool(**kwargs):
            """
            When Celery fork's the parent process, the db engine & connection pool is included in that.
            But, the db connections should not be shared across processes, so we tell the engine
            to dispose of all existing connections, which will cause new ones to be opend in the child
            processes as needed.
            More info: https://docs.sqlalchemy.org/en/latest/core/pooling.html#using-connection-pools-with-multiprocessing
            """
            # The "with" here is for a flask app using Flask-SQLAlchemy.  If you don't
            # have a flask app, just remove the "with" here and call .dispose()
            # on your SQLAlchemy db engine.
            flask_app.logger.info("Disposing of existing database connections.")
            with flask_app.app_context():
                db.engine.dispose()

        flask_app.logger.info("Celery app created.")
        return celery_app

    @classmethod
    def _create_flask_app(cls, config: Config) -> Flask:
        """Create minimal flask app with just database setup."""
        app = Flask(__name__)
        app.config.from_mapping(config.flask_config)
        with app.app_context():
            setup_db(app)
        return app

    @staticmethod
    def _setup_logging(
        level: Literal[
            "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"
        ] = "INFO"
    ) -> None:
        dictConfig(
            {
                "version": 1,
                "formatters": {
                    "default": {
                        "format": (
                            "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
                        ),
                    }
                },
                "handlers": {
                    "wsgi": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://flask.logging.wsgi_errors_stream",
                        "formatter": "default",
                    }
                },
                # "root": {"level": level, "handlers": ["wsgi"]},
            }
        )
