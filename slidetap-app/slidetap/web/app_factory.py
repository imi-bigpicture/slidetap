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

"""Factory for creating the Flask application."""

from typing import Dict, Iterable, Optional

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_uuid import FlaskUUID

from slidetap.config import Config
from slidetap.database.db import setup_db
from slidetap.flask_extension import FlaskExtension
from slidetap.logging import setup_logging
from slidetap.services import (
    AttributeService,
    AuthService,
    ImageService,
    ItemService,
    LoginService,
    MapperService,
    ProjectService,
    SchemaService,
)
from slidetap.services.preview_service import PreviewService
from slidetap.services.processing_service import ProcessingService
from slidetap.services.validation_service import ValidationService
from slidetap.task.app_factory import (
    SlideTapTaskAppFactory,
    TaskClassFactory,
)
from slidetap.web.controller import (
    AttributeController,
    Controller,
    ImageController,
    ItemController,
    LoginController,
    MapperController,
    ProjectController,
    SchemaController,
)
from slidetap.web.exporter import ImageExporter, MetadataExporter
from slidetap.web.importer import ImageImporter, Importer, MetadataImporter


class SlideTapWebAppFactory:
    """Factory for creating a Flask app to run."""

    @classmethod
    def create(
        cls,
        auth_service: AuthService,
        login_service: LoginService,
        login_controller: LoginController,
        image_importer: ImageImporter,
        image_exporter: ImageExporter,
        metadata_importer: MetadataImporter,
        metadata_exporter: MetadataExporter,
        config: Optional[Config] = None,
        extra_extensions: Optional[Iterable[FlaskExtension]] = None,
        celery_task_class_factory: Optional[TaskClassFactory] = None,
    ) -> Flask:
        """Create a SlideTap flask app using supplied implementations.

        Parameters
        ----------
        auth_service: AuthService
            AuthService to use to verify user credentials.
        image_importer: ImageImporter
            ImageImporter to use for searching for and downloading images.
        image_exporter: ImageExporter
            ImageExporter to use for processing downloaded images and moving
            to storage.
        metadata_importer: MetadataImporter
            MetadataImporter to use for searching for metadata.
        metadata_exporter: MetadataExporter
            MetadataExporter to use for formatting metadata and moveing to
            storage.
        config: Optional[Config] = None
            Optional configuration to use. If not configuration will be
            read from environment variables.
        extra_extensions: Optional[Iterable[FlaskExtension]] = None
            Optional extra extensions to add to the app.

        Returns
        ----------
        Flask
            Created Flask application.

        """

        if config is None:
            config = Config()
        cls._check_https_url(config)
        setup_logging(config.flask_log_level)
        app = Flask(__name__)

        app.config.from_mapping(config.flask_config)
        app.logger.setLevel(config.flask_log_level)
        app.logger.info("Creating SlideTap Flask app.")
        app.logger.log(
            app.logger.level,
            f"Running on log level {app.logger.level} "
            f"with effective level {app.logger.getEffectiveLevel()}.",
        )

        db = cls._setup_db(app)
        flask_uuid = FlaskUUID()
        flask_uuid.init_app(app)
        cls._init_extensions(
            app,
            [
                auth_service,
                login_service,
                metadata_importer,
                image_importer,
                metadata_exporter,
                image_exporter,
            ],
            extra_extensions,
        )
        cls._register_importers(app, [image_importer, metadata_importer])
        validation_service = ValidationService()
        mapper_service = MapperService(validation_service)
        schema_service = SchemaService(metadata_importer.schema.uid)
        attribute_service = AttributeService(schema_service, validation_service)
        project_service = ProjectService(attribute_service)
        image_service = ImageService(image_exporter.storage)
        item_service = ItemService(attribute_service, validation_service)
        processing_service = ProcessingService(
            image_importer,
            image_exporter,
            metadata_importer,
            metadata_exporter,
            project_service,
        )
        preview_service = PreviewService(metadata_exporter)
        cls._create_and_register_controllers(
            app,
            login_service,
            login_controller,
            project_service,
            item_service,
            attribute_service,
            schema_service,
            mapper_service,
            image_service,
            validation_service,
            processing_service,
            preview_service,
        )
        cls._setup_cors(app, config)
        if config.restore_projects:
            processing_service.restore_all_projects(app)
        if celery_task_class_factory is None:
            app.logger.info("Creating celery app.")
            celery_app = SlideTapTaskAppFactory.create_celery_flask_app(
                flask_app=app, config=config
            )
        else:
            app.logger.info("Creating flask app with celery worker.")
            celery_app = SlideTapTaskAppFactory.create_celery_worker_app(
                config, celery_task_class_factory, flask_app=app
            )
        app.extensions["celery"] = celery_app
        app.logger.info("Celery app created.")
        app.logger.info("SlideTap Flask app created.")
        return app

    @staticmethod
    def _init_extensions(
        app: Flask,
        extensions: Iterable[FlaskExtension],
        extra_extensions: Optional[Iterable[FlaskExtension]],
    ):
        """Initiate flask extensions (that has init_app()-method).

        Parameters
        ----------
        app: Flask
            App to init extensions with.
        extensions: Sequence[FlaskExtension]
            Extension to init.

        """
        app.logger.info("Initiating Flask app extensions.")
        if extra_extensions is not None:
            for extension in extra_extensions:
                extension.init_app(app)
        for extension in extensions:
            extension.init_app(app)
        app.logger.info("Flask app extensions initiated.")

    @staticmethod
    def _register_importers(app: Flask, importers: Iterable[Importer]):
        """Register the blueprint for importers.

        Parameters
        ----------
        app: Flask
            App to register blueprint with.
        importers: Sequence[Importer]
            Importers to register.

        """
        app.logger.info("Registering Flask app importers.")
        for importer in importers:
            if (
                importer.blueprint is not None
                and importer.blueprint.name not in app.blueprints.keys()
            ):
                app.register_blueprint(importer.blueprint)
        app.logger.info("Flask app importers registered.")

    @staticmethod
    def _create_and_register_controllers(
        app: Flask,
        login_service: LoginService,
        login_controller: LoginController,
        project_service: ProjectService,
        item_service: ItemService,
        attribute_service: AttributeService,
        schema_service: SchemaService,
        mapper_service: MapperService,
        image_service: ImageService,
        validation_service: ValidationService,
        processing_service: ProcessingService,
        preview_service: PreviewService,
    ):
        """Create and register the blueprint for importers.

        Parameters
        ----------
        app: Flask
            App to register blueprint with.
        login_service: LoginService
            Login service to use for controllers.
        login_controller: LoginController
        project_service: ProjectService
        attribute_service: AttributeService
        mapper_service: MapperService
        image_service: ImageService
        """
        app.logger.info("Creating and registering Flask app controllers.")
        controllers: Dict[str, Controller] = {
            "/api/auth": login_controller,
            "/api/project": ProjectController(
                login_service, project_service, validation_service, processing_service
            ),
            "/api/attribute": AttributeController(
                login_service,
                attribute_service,
                schema_service,
                mapper_service,
                validation_service,
            ),
            "/api/mapper": MapperController(
                login_service, mapper_service, attribute_service, schema_service
            ),
            "/api/image": ImageController(login_service, image_service),
            "/api/item": ItemController(
                login_service,
                item_service,
                schema_service,
                validation_service,
                preview_service,
                processing_service,
            ),
            "/api/schema": SchemaController(login_service, schema_service),
        }
        [
            app.register_blueprint(controller.blueprint, url_prefix=url_prefix)
            for url_prefix, controller in controllers.items()
        ]
        app.logger.info("Flask app controllers created and registered.")

    @staticmethod
    def _setup_cors(app: Flask, config: Config):
        CORS(
            app,
            resources={
                r"/api/*": {"origins": config.webapp_url, "supports_credentials": True}
            },
        )

    @staticmethod
    def _setup_db(app: Flask) -> SQLAlchemy:
        with app.app_context():
            return setup_db(app)

    @staticmethod
    def _check_https_url(config: Config) -> None:
        """If enforce https is true check that urls are https."""
        if not config.enforce_https:
            return
        if not config.webapp_url.startswith("https://"):
            raise ValueError(
                f"Https required but {config.webapp_url} ",
                "is not https.",
            )
