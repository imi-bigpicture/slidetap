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

"""Factory for creating the FastAPI application."""

import logging
from typing import Dict, Iterable, Optional

from celery import Celery
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from slidetap.web.routers import (
    AttributeRouter,
    BatchRouter,
    DatasetRouter,
    ImageRouter,
    ItemRouter,
    LoginRouter,
    MapperRouter,
    ProjectRouter,
    SchemaRouter,
)
from slidetap.web.services import (
    AuthService,
    ImageExportService,
    ImageImportService,
    MetadataExportService,
    MetadataImportService,
)


class SlideTapAppFactory:
    """Factory for creating a FastAPI app to run."""

    @classmethod
    def create(
        cls,
        auth_service: AuthService,
        login_router: LoginRouter,
        metadata_import_interface: MetadataImportInterface[MetadataSearchParameterType],
        metadata_export_interface: MetadataExportInterface,
        service_provider: ServiceProvider,
        config: Optional[Config] = None,
        celery_app: Optional[Celery] = None,
    ) -> FastAPI:
        """Create a SlideTap FastAPI app using supplied implementations.

        Parameters
        ----------
        auth_service: AuthService
            AuthService to use to verify user credentials.
        login_service: LoginService
            LoginService to handle user authentication.
        login_router: LoginRouter
            LoginRouter to handle authentication endpoints.
        metadata_import_interface: MetadataImportInterface
            Interface for importing metadata.
        metadata_export_interface: MetadataExportInterface
            Interface for exporting metadata.
        service_provider: ServiceProvider
            Provider for various services.
        config: Optional[Config] = None
            Optional configuration to use. If not configuration will be
            read from environment variables.
        celery_app: Optional[Celery] = None
            Optional Celery app instance.

        Returns
        ----------
        FastAPI
            Created FastAPI application.

        """

        if config is None:
            config = Config()
        cls._check_https_url(config)
        # TODOD
        # setup_logging(config.flask_log_level)

        app = FastAPI(
            title="SlideTap API",
            description="SlideTap application API",
            version="0.2.0",
        )

        logger = logging.getLogger(__name__)
        logger.setLevel(config.flask_log_level)
        logger.info("Creating SlideTap FastAPI app.")

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

        cls._create_and_register_routers(
            app,
            login_router,
            service_provider,
            metadata_import_service,
            metadata_export_service,
            image_import_service,
            image_export_service,
        )
        cls._setup_cors(app, config)

        logger.info("Creating celery app.")
        if celery_app is None:
            celery_app = SlideTapTaskAppFactory.create_celery_flask_app(
                name="slidetap", config=config
            )

        app.state.celery = celery_app
        app.state.config = config
        app.state.auth_service = auth_service

        logger.info("Celery app created.")
        logger.info("SlideTap FastAPI app created.")
        return app

    @staticmethod
    def _create_and_register_routers(
        app: FastAPI,
        login_router: LoginRouter,
        service_provider: ServiceProvider,
        metadata_import_service: MetadataImportService,
        metadata_export_service: MetadataExportService,
        image_import_service: ImageImportService,
        image_export_service: ImageExportService,
    ):
        """Create and register the routers.

        Parameters
        ----------
        app: FastAPI
            App to register routers with.
        login_router: LoginRouter
            Login router to use for authentication.
        login_service: LoginService
            Login service to use for routers.
        service_provider: ServiceProvider
            Service provider for various services.
        metadata_import_service: MetadataImportService
            Service for importing metadata.
        metadata_export_service: MetadataExportService
            Service for exporting metadata.
        image_import_service: ImageImportService
            Service for importing images.
        image_export_service: ImageExportService
            Service for exporting images.
        """
        logger = logging.getLogger(__name__)
        logger.info("Creating and registering FastAPI routers.")

        # Register routers
        app.include_router(login_router.router, prefix="/api/auth", tags=["auth"])

        project_router = ProjectRouter(
            service_provider.project_service,
            service_provider.validation_service,
            service_provider.batch_service,
            service_provider.dataset_service,
            service_provider.database_service,
            metadata_import_service,
            metadata_export_service,
        )
        app.include_router(
            project_router.router, prefix="/api/projects", tags=["project"]
        )

        attribute_router = AttributeRouter(
            service_provider.attribute_service,
            service_provider.schema_service,
            service_provider.mapper_service,
            service_provider.validation_service,
        )
        app.include_router(
            attribute_router.router, prefix="/api/attributes", tags=["attribute"]
        )

        mapper_router = MapperRouter(
            service_provider.mapper_service,
            service_provider.attribute_service,
            service_provider.schema_service,
        )
        app.include_router(mapper_router.router, prefix="/api/mappers", tags=["mapper"])

        image_router = ImageRouter(service_provider.image_service)
        app.include_router(image_router.router, prefix="/api/images", tags=["image"])

        item_router = ItemRouter(
            service_provider.item_service,
            service_provider.schema_service,
            service_provider.validation_service,
            service_provider.database_service,
            metadata_export_service,
            image_import_service,
            image_export_service,
        )
        app.include_router(item_router.router, prefix="/api/items", tags=["item"])

        schema_router = SchemaRouter(service_provider.schema_service)
        app.include_router(schema_router.router, prefix="/api/schemas", tags=["schema"])

        dataset_router = DatasetRouter(
            service_provider.project_service,
            service_provider.dataset_service,
        )
        app.include_router(
            dataset_router.router, prefix="/api/datasets", tags=["dataset"]
        )

        batch_router = BatchRouter(
            service_provider.batch_service,
            service_provider.validation_service,
            service_provider.schema_service,
            service_provider.database_service,
            metadata_import_service,
            image_import_service,
            image_export_service,
        )
        app.include_router(batch_router.router, prefix="/api/batches", tags=["batch"])

        logger.info("FastAPI routers created and registered.")

    @staticmethod
    def _setup_cors(app: FastAPI, config: Config):
        """Setup CORS middleware for the FastAPI app."""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[config.webapp_url],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
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
