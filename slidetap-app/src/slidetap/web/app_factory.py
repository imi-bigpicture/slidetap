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
from collections.abc import Sequence
from contextlib import asynccontextmanager

from dishka.async_container import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from procrastinate import App as TaskApp
from starlette.routing import Mount, Route, WebSocketRoute

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
        extra_routers: Sequence[APIRouter] | None = None,
    ) -> FastAPI:
        """Create a SlideTap FastAPI app using supplied implementations.

        Parameters
        ----------
        container : AsyncContainer
            Dependency injection container for the application.
        extra_routers : Sequence[APIRouter] | None = None
            Optional flavor-specific routers registered after the built-in
            routers.

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
        cls._create_and_register_routers(app, extra_routers)
        logger.info("SlideTap FastAPI app created.")
        return app

    @classmethod
    def _create_and_register_routers(
        cls,
        app: FastAPI,
        extra_routers: Sequence[APIRouter] | None = None,
    ):
        """Create and register the routers."""
        logger = logging.getLogger(f"{__name__}.{cls.__name__}")
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

        if extra_routers:
            cls._register_extra_routers(app, extra_routers)

        logger.info("FastAPI routers created and registered.")

    @classmethod
    def _register_extra_routers(
        cls,
        app: FastAPI,
        extra_routers: Sequence[APIRouter],
    ):
        """Register flavor-supplied routers, rejecting path collisions.

        Path collisions are checked strictly: an extension route may not
        reuse any path already registered by a built-in router or by an
        earlier extension router, regardless of HTTP method.

        Note: for Mount routes only the mount prefix is checked; collisions
        nested inside a mounted sub-app are not detected.
        """
        logger = logging.getLogger(f"{__name__}.{cls.__name__}")
        builtin_paths: set[str] = {
            route.path
            for route in app.routes
            if isinstance(route, (Route, WebSocketRoute, Mount))
        }
        seen_extension_paths: set[str] = set()
        for router in extra_routers:
            for route in router.routes:
                if not isinstance(route, (Route, WebSocketRoute, Mount)):
                    continue
                full_path = f"{router.prefix}{route.path}"
                if full_path in builtin_paths:
                    raise ValueError(
                        f"Extension router path {full_path} collides with a "
                        "built-in route"
                    )
                if full_path in seen_extension_paths:
                    raise ValueError(
                        f"Extension router path {full_path} is registered by "
                        "multiple extension routers"
                    )
                seen_extension_paths.add(full_path)
            app.include_router(router)
            logger.info(
                f"Registered extension router: {router.prefix or '(no prefix)'}"
            )

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
