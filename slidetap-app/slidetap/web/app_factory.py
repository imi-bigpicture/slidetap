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

from celery import Celery
from flask import Flask
from flask_cors import CORS
from flask_uuid import FlaskUUID

from slidetap.config import Config
from slidetap.external_interfaces import (
    MetadataExportInterface,
    MetadataImportInterface,
    MetadataSearchParameterType,
)
from slidetap.logging import setup_logging
from slidetap.service_provider import ServiceProvider
from slidetap.task import Scheduler
from slidetap.task.app_factory import SlideTapTaskAppFactory
from slidetap.web.controller import (
    AttributeController,
    BatchController,
    Controller,
    DatasetController,
    ImageController,
    ItemController,
    LoginController,
    MapperController,
    ProjectController,
    SchemaController,
)
from slidetap.web.flask_extension import FlaskExtension
from slidetap.web.services import (
    AuthService,
    ImageExportService,
    ImageImportService,
    LoginService,
    MetadataExportService,
    MetadataImportService,
)


class SlideTapWebAppFactory:
    """Factory for creating a Flask app to run."""

    @classmethod
    def create(
        cls,
        auth_service: AuthService,
        login_service: LoginService,
        login_controller: LoginController,
        metadata_import_interface: MetadataImportInterface[MetadataSearchParameterType],
        metadata_export_interface: MetadataExportInterface,
        service_provider: ServiceProvider,
        config: Optional[Config] = None,
        extra_extensions: Optional[Iterable[FlaskExtension]] = None,
        celery_app: Optional[Celery] = None,
    ) -> Flask:
        """Create a SlideTap flask app using supplied implementations.

        Parameters
        ----------
        auth_service: AuthService
            AuthService to use to verify user credentials.
        image_importer: ImageImportService
            ImageImportService to use for searching for and downloading images.
        image_exporter: ImageExportService
            ImageExportService to use for processing downloaded images and moving
            to storage.
        metadata_importer: MetadataImportService
            MetadataImportService to use for searching for metadata.
        metadata_exporter: MetadataExportService
            MetadataExportService to use for formatting metadata and moveing to
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

        flask_uuid = FlaskUUID()
        flask_uuid.init_app(app)
        cls._init_extensions(
            app,
            [
                auth_service,
                login_service,
            ],
            extra_extensions,
        )
        scheduler = Scheduler()
        metadata_import_service = MetadataImportService(
            scheduler, metadata_import_interface
        )
        metadata_export_service = MetadataExportService(
            scheduler,
            service_provider.project_service,
            service_provider.database_service,
            metadata_export_interface,
        )
        image_import_service = ImageImportService(
            scheduler,
            service_provider.database_service,
            list(service_provider.schema_service.images.values()),
        )
        image_export_service = ImageExportService(
            scheduler,
            service_provider.database_service,
            list(service_provider.schema_service.images.values()),
        )
        cls._create_and_register_controllers(
            app,
            login_controller,
            login_service,
            service_provider,
            metadata_import_service,
            metadata_export_service,
            image_import_service,
            image_export_service,
        )
        cls._setup_cors(app, config)
        app.logger.info("Creating celery app.")
        if celery_app is None:
            celery_app = SlideTapTaskAppFactory.create_celery_flask_app(
                name=app.name, config=config
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
    def _create_and_register_controllers(
        app: Flask,
        login_controller: LoginController,
        login_service: LoginService,
        service_provider: ServiceProvider,
        metadata_import_service: MetadataImportService,
        metadata_export_service: MetadataExportService,
        image_import_service: ImageImportService,
        image_export_service: ImageExportService,
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
                login_service,
                service_provider.project_service,
                service_provider.validation_service,
                service_provider.batch_service,
                service_provider.dataset_service,
                service_provider.database_service,
                metadata_import_service,
                metadata_export_service,
            ),
            "/api/attribute": AttributeController(
                login_service,
                service_provider.attribute_service,
                service_provider.schema_service,
                service_provider.mapper_service,
                service_provider.validation_service,
            ),
            "/api/mapper": MapperController(
                login_service,
                service_provider.mapper_service,
                service_provider.attribute_service,
                service_provider.schema_service,
            ),
            "/api/image": ImageController(
                login_service, service_provider.image_service
            ),
            "/api/item": ItemController(
                login_service,
                service_provider.item_service,
                service_provider.schema_service,
                service_provider.validation_service,
                service_provider.database_service,
                metadata_export_service,
                image_import_service,
                image_export_service,
            ),
            "/api/schema": SchemaController(
                login_service, service_provider.schema_service
            ),
            "/api/dataset": DatasetController(
                login_service,
                service_provider.project_service,
                service_provider.dataset_service,
            ),
            "/api/batch": BatchController(
                login_service,
                service_provider.batch_service,
                service_provider.validation_service,
                service_provider.schema_service,
                service_provider.database_service,
                metadata_import_service,
                image_import_service,
                image_export_service,
            ),
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
    def _check_https_url(config: Config) -> None:
        """If enforce https is true check that urls are https."""
        if not config.enforce_https:
            return
        if not config.webapp_url.startswith("https://"):
            raise ValueError(
                f"Https required but {config.webapp_url} ",
                "is not https.",
            )
