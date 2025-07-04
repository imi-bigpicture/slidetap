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
from typing import Optional

from celery import Celery
from dishka.async_container import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slidetap.config import Config
from slidetap.services import ImageCache, MapperInjector
from slidetap.task.app_factory import SlideTapTaskAppFactory
from slidetap.web.routers import (
    attribute_router,
    batch_router,
    dataset_router,
    image_router,
    item_router,
    login_router,
    mapper_router,
    project_router,
    schema_router,
    tag_router,
)
from slidetap.web.services import LoginService


@asynccontextmanager
async def lifespan(app: FastAPI):
    container: AsyncContainer = app.state.dishka_container
    injector: Optional[MapperInjector] = await container.get(Optional[MapperInjector])
    if injector is not None:
        injector.inject()
    yield
    image_cache = await container.get(ImageCache)
    image_cache.close()


class SlideTapWebAppFactory:
    """Factory for creating a FastAPI app to run."""

    @classmethod
    def create(
        cls,
        config: Config,
        container: AsyncContainer,
        celery_app: Optional[Celery] = None,
    ) -> FastAPI:
        """Create a SlideTap FastAPI app using supplied implementations.

        Parameters
        ----------
        config : Config
            Configuration for the application.
        container : AsyncContainer
            Dependency injection container for the application.

        Returns
        ----------
        FastAPI
            Created FastAPI application.

        """

        # TODOD
        # setup_logging(config.flask_log_level)
        cls._check_https_url(config)
        app = FastAPI(
            title="SlideTap API",
            description="SlideTap application API",
            version="0.2.0",
            lifespan=lifespan,
        )
        setup_dishka(container=container, app=app)

        logger = logging.getLogger(__name__)
        logger.setLevel(config.web_app_log_level)
        logger.info("Creating SlideTap FastAPI app.")

        cls._setup_cors(app, config)
        cls._create_and_register_routers(app)

        logger.info("Creating celery app.")
        if celery_app is None:
            celery_app = SlideTapTaskAppFactory.create_celery_web_app(
                name="slidetap", config=config
            )
        app.state.celery_app = celery_app
        logger.info("Celery app created.")
        logger.info("SlideTap FastAPI app created.")
        return app

    @staticmethod
    def _create_and_register_routers(app: FastAPI):
        """Create and register the routers."""
        logger = logging.getLogger(__name__)
        logger.info("Creating and registering FastAPI routers.")

        app.include_router(login_router)
        app.include_router(attribute_router)
        app.include_router(batch_router)
        app.include_router(dataset_router)
        app.include_router(image_router)
        app.include_router(item_router)
        app.include_router(mapper_router)
        app.include_router(project_router)
        app.include_router(schema_router)
        app.include_router(tag_router)

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
