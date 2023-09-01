"""Factory for creating the Flask application."""
from logging.config import dictConfig
from typing import Dict, Iterable, Literal, Optional

from flask import Flask
from flask_cors import CORS
from flask_uuid import FlaskUUID

from slides.config import Config
from slides.controller import (
    Controller,
    ImageController,
    LoginController,
    MapperController,
    ProjectController,
)
from slides.controller.attribute_controller import AttributeController
from slides.database.db import setup_db

from slides.exporter import ImageExporter, MetadataExporter
from slides.flask_extension import FlaskExtension
from slides.importer import ImageImporter, Importer, MetadataImporter
from slides.services import AuthService, LoginService
from slides.services.attribute_service import AttributeService
from slides.services.image_service import ImageCache, ImageService
from slides.services.mapper_service import MapperService
from slides.services.project_service import ProjectService


class SlidesAppFactory:
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
    ) -> Flask:
        """Create a Slides flask app using supplied implementations.

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

        Returns
        ----------
        Flask
            Created Flask application.

        """
        if config is None:
            config = Config()
        cls._setup_logging("DEBUG")
        app = Flask(__name__)
        flask_uuid = FlaskUUID()
        flask_uuid.init_app(app)
        app.secret_key = config.SLIDES_SECRET_KEY
        cls._check_https_url(config)
        app.config.from_object(config)
        cls._setup_db(app)
        cls._init_extensions(
            app,
            [
                auth_service,
                login_service,
                image_importer,
                metadata_importer,
                image_exporter,
            ],
            extra_extensions,
        )
        cls._register_importers(app, [image_importer, metadata_importer])

        project_service = ProjectService(
            image_importer, image_exporter, metadata_importer, metadata_exporter
        )
        image_service = ImageService(image_exporter.storage)
        mapper_service = MapperService()
        attribute_service = AttributeService()
        cls._create_and_register_controllers(
            app,
            login_service,
            login_controller,
            project_service,
            attribute_service,
            mapper_service,
            image_service,
        )
        cls._setup_cors(app)
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
        if extra_extensions is not None:
            for extension in extra_extensions:
                extension.init_app(app)
        for extension in extensions:
            extension.init_app(app)

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
        for importer in importers:
            if importer.blueprint is not None:
                app.register_blueprint(importer.blueprint)

    @staticmethod
    def _create_and_register_controllers(
        app: Flask,
        login_service: LoginService,
        login_controller: LoginController,
        project_service: ProjectService,
        attribute_service: AttributeService,
        mapper_service: MapperService,
        image_service: ImageService,
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
        controllers: Dict[str, Controller] = {
            "/api/auth": login_controller,
            "/api/project": ProjectController(login_service, project_service),
            "/api/attribute": AttributeController(
                login_service, attribute_service, mapper_service
            ),
            "/api/mapper": MapperController(
                login_service, mapper_service, attribute_service
            ),
            "/api/image": ImageController(login_service, image_service),
        }
        [
            app.register_blueprint(controller.blueprint, url_prefix=url_prefix)
            for url_prefix, controller in controllers.items()
        ]

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
                "root": {"level": level, "handlers": ["wsgi"]},
            }
        )

    @staticmethod
    def _setup_cors(app: Flask):
        origin = app.config["SLIDES_WEBAPPURL"]
        CORS(
            app,
            resources={r"/api/*": {"origins": origin, "supports_credentials": True}},
        )

    @staticmethod
    def _setup_db(app: Flask):
        with app.app_context():
            setup_db(app)
            # add_test_mappers()

    @staticmethod
    def _check_https_url(config: Config) -> None:
        """If enforce https is true check that urls are https."""
        if not config.SLIDES_ENFORCE_HTTPS:
            return
        if not config.SLIDES_WEBAPPURL.startswith("https://"):
            raise ValueError(
                f"Https required but {config.SLIDES_WEBAPPURL} ",
                "is not https.",
            )
