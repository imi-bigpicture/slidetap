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
from contextlib import asynccontextmanager

from dishka.async_container import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from procrastinate import App as TaskApp

from slidetap.config import SlideTapConfig
from slidetap.logging import setup_logging
from slidetap.services import ImageCache
from slidetap.web.routers import (
    attribute_router,
    batch_router,
    dataset_router,
    health_router,
    image_router,
    item_router,
    login_router,
    mapper_router,
    metadata_search_router,
    project_router,
    schema_router,
    tag_router,
)


class SlideTapWebAppFactory:
    """Factory for creating a FastAPI app to run."""

    @classmethod
    def create(
        cls,
        container: AsyncContainer,
    ) -> FastAPI:
        """Create a SlideTap FastAPI app using supplied implementations.

        Parameters
        ----------
        container : AsyncContainer
            Dependency injection container for the application.

        Returns
        ----------
        FastAPI
            Created FastAPI application.

        """
        logger = logging.getLogger(f"{__name__}.{cls.__name__}")

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Async lifespan context for the FastAPI app."""
            config = await container.get(SlideTapConfig)
            logger.setLevel(config.web_app_log_level)
            setup_logging(config.logging_config)
            logger.info("Starting SlideTap FastAPI app.")

            if config.cors_origins:
                cls._setup_cors(app, config.cors_origins)

            task_app = await container.get(TaskApp)
            async with task_app.open_async():
                logger.info("SlideTap FastAPI app started.")
                yield
                logger.info("Shutting down SlideTap FastAPI app.")

            image_cache = await container.get(ImageCache)
            image_cache.close()
            logger.info("SlideTap FastAPI app shut down.")

        logger.info("Creating SlideTap FastAPI app.")
        app = FastAPI(
            title="SlideTap API",
            description="SlideTap application API",
            version="0.2.0",
            lifespan=lifespan,
        )
        setup_dishka(container=container, app=app)
        cls._create_and_register_routers(app)
        logger.info("SlideTap FastAPI app created.")
        return app

    @staticmethod
    def _create_and_register_routers(app: FastAPI):
        """Create and register the routers."""
        logger = logging.getLogger(__name__)
        logger.info("Creating and registering FastAPI routers.")
        app.include_router(health_router)
        app.include_router(login_router)
        app.include_router(attribute_router)
        app.include_router(batch_router)
        app.include_router(dataset_router)
        app.include_router(image_router)
        app.include_router(item_router)
        app.include_router(mapper_router)
        app.include_router(metadata_search_router)
        app.include_router(project_router)
        app.include_router(schema_router)
        app.include_router(tag_router)

        logger.info("FastAPI routers created and registered.")

    @staticmethod
    def _setup_cors(app: FastAPI, cors_origins: str):
        """Setup CORS middleware for the FastAPI app."""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[cors_origins],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
