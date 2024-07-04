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

from typing import Optional

from celery import Celery, Task
from flask import Flask

from slidetap.config import Config
from slidetap.database import setup_db
from slidetap.tasks.processors import (
    ImagePostProcessor,
    ImagePreProcessor,
    MetadataExportProcessor,
    MetadataImportProcessor,
    processor_container,
)


class SlideTapCeleryAppFactory:
    @classmethod
    def create(
        cls,
        image_pre_processor: Optional[ImagePreProcessor] = None,
        image_post_processor: Optional[ImagePostProcessor] = None,
        metadata_export_processor: Optional[MetadataExportProcessor] = None,
        metadata_import_processor: Optional[MetadataImportProcessor] = None,
        config: Optional[Config] = None,
    ):
        if config is None:
            config = Config()
        processor_container.init_processors(
            image_pre_processor,
            image_post_processor,
            metadata_export_processor,
            metadata_import_processor,
        )
        flask_app = cls._create_flask_app(config)
        flask_app.logger.info("Creating SlideTap Celery Flask app.")
        processor_container.init_app(flask_app)
        flask_app.logger.info("SlideTap Celery Flask app created.")
        celery_app = cls._create_celery_app(flask_app, config)

        return celery_app

    @classmethod
    def _create_celery_app(cls, flask_app: Flask, config: Config) -> Celery:
        class FlaskTask(Task):
            def __call__(self, *args: object, **kwargs: object) -> object:
                with flask_app.app_context():
                    return self.run(*args, **kwargs)

        celery_app = Celery(flask_app.name, task_cls=FlaskTask)
        celery_app.config_from_object(config.celery_config)
        celery_app.set_default()
        return celery_app

    @classmethod
    def _create_flask_app(cls, config: Config) -> Flask:
        app = Flask(__name__)
        app.config.from_mapping(config.flask_config)
        with app.app_context():
            setup_db(app)
        return app
