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
from typing import Any, Literal, Optional, Sequence, Type

from celery import Celery, Task
from celery.signals import worker_process_init
from celery.utils.log import get_task_logger
from flask import Flask

from slidetap.config import Config
from slidetap.database import db, setup_db
from slidetap.task.processors import (
    ImagePostProcessor,
    ImagePreProcessor,
    MetadataExportProcessor,
    MetadataImportProcessor,
)
from slidetap.task.processors.image.image_downloader import ImageDownloader
from slidetap.task.processors.processor_factory import ProcessorFactory


class CeleryTaskClassFactory:
    def __init__(
        self,
        image_downloader_factory: Optional[
            ProcessorFactory[ImageDownloader, Any]
        ] = None,
        image_pre_processor_factory: Optional[
            ProcessorFactory[ImagePreProcessor, Any]
        ] = None,
        image_post_processor_factory: Optional[
            ProcessorFactory[ImagePostProcessor, Any]
        ] = None,
        metadata_export_processor_factory: Optional[
            ProcessorFactory[MetadataExportProcessor, Any]
        ] = None,
        metadata_import_processor_factory: Optional[
            ProcessorFactory[MetadataImportProcessor, Any]
        ] = None,
    ):
        self.image_downloader_factory = image_downloader_factory
        self.image_pre_processor_factory = image_pre_processor_factory
        self.image_post_processor_factory = image_post_processor_factory
        self.metadata_export_processor_factory = metadata_export_processor_factory
        self.metadata_import_processor_factory = metadata_import_processor_factory

    def create(self, flask_app: Flask) -> Type[Task]:
        image_downloader_factory = self.image_downloader_factory
        image_pre_processor_factory = self.image_pre_processor_factory
        image_post_processor_factory = self.image_post_processor_factory
        metadata_export_processor_factory = self.metadata_export_processor_factory
        metadata_import_processor_factory = self.metadata_import_processor_factory
        flask_app.logger.info("Creating Celery task class.")

        class FlaskTask(Task):
            def __call__(self, *args: object, **kwargs: object) -> object:
                with flask_app.app_context():
                    return self.run(*args, **kwargs)

            @cached_property
            def logger(self):
                return get_task_logger(self.name)

            @cached_property
            def image_downloader(self) -> ImageDownloader:
                if image_downloader_factory is None:
                    self.logger.error("Image downloader factory not set.")
                    raise ValueError("Image downloader factory not set.")
                with flask_app.app_context():
                    self.logger.info("Creating image downloader.")
                    return image_downloader_factory.create(flask_app)

            @cached_property
            def image_pre_processor(self) -> ImagePreProcessor:
                if image_pre_processor_factory is None:
                    self.logger.error("Image pre-processor factory not set.")
                    raise ValueError("Image pre-processor factory not set.")
                with flask_app.app_context():
                    self.logger.info("Creating image pre-processor.")
                    return image_pre_processor_factory.create(flask_app)

            @cached_property
            def image_post_processor(self) -> ImagePostProcessor:
                if image_post_processor_factory is None:
                    self.logger.error("Image post-processor factory not set.")
                    raise ValueError("Image post-processor factory not set.")
                with flask_app.app_context():
                    self.logger.info("Creating image post-processor.")
                    return image_post_processor_factory.create(flask_app)

            @cached_property
            def metadata_export_processor(self) -> MetadataExportProcessor:
                if metadata_export_processor_factory is None:
                    self.logger.error("Metadata export processor factory not set.")
                    raise ValueError("Metadata export processor factory not set.")
                with flask_app.app_context():
                    self.logger.info("Creating metadata export processor.")
                    return metadata_export_processor_factory.create(flask_app)

            @cached_property
            def metadata_import_processor(self) -> MetadataImportProcessor:
                if metadata_import_processor_factory is None:
                    self.logger.error("Metadata import processor factory not set.")
                    raise ValueError("Metadata import processor factory not set.")
                with flask_app.app_context():
                    self.logger.info("Creating metadata import processor.")
                    return metadata_import_processor_factory.create(flask_app)

        return FlaskTask


class SlideTapTaskAppFactory:
    @classmethod
    def create_celery_worker_app(
        cls,
        config: Config,
        celery_task_class_factory: CeleryTaskClassFactory,
        include: Optional[Sequence[str]] = None,
        flask_app: Optional[Flask] = None,
    ):
        """Create a Celery application for worker usage."""
        cls._setup_logging(config.flask_log_level)
        if flask_app is None:
            flask_app = cls._create_flask_app(config)
        flask_app.logger.info("Creating SlideTap Celery worker app.")
        task_class = celery_task_class_factory.create(flask_app)

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

        celery_app = cls._create_celery_app(flask_app.name, config, task_class, include)
        flask_app.logger.info("SlideTap Celery worker app created.")
        return celery_app

    @classmethod
    def create_celery_flask_app(
        cls,
        flask_app: Flask,
        config: Config,
    ):
        """Create a Celery application for flask usage."""
        return cls._create_celery_app(flask_app.name, config)

    @classmethod
    def _create_celery_app(
        cls,
        name: str,
        config: Config,
        task_cls: Optional[Type[Task]] = None,
        include: Optional[Sequence[str]] = None,
    ):
        """Create a Celery application."""
        if task_cls is None:
            task_cls = Task
        if include is None:
            include = []
        celery_app = Celery(name, task_cls=task_cls, include=include)
        celery_app.config_from_object(config.celery_config)
        celery_app.set_default()
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
