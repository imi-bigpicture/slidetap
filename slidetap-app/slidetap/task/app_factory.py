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

"""Factory for creating a Celery application."""

import logging
from typing import Optional, Sequence

from celery import Celery
from dishka import Container
from dishka.integrations.celery import DishkaTask, setup_dishka

from slidetap.config import Config
from slidetap.logging import setup_logging


class SlideTapTaskAppFactory:
    @classmethod
    def create_celery_worker_app(
        cls,
        name: str,
        config: Config,
        container: Container,
        include: Optional[Sequence[str]] = None,
    ):
        """Create a Celery application for worker usage."""
        # setup_logging(config.web_app_log_level)

        logging.info("Creating SlideTap Celery worker app.")
        celery_app = cls._create_celery_app(name=name, config=config, include=include)
        setup_dishka(container=container, app=celery_app)
        logging.info("SlideTap Celery worker app created.")
        return celery_app

    @classmethod
    def create_celery_web_app(
        cls,
        name: str,
        config: Config,
    ):
        """Create a Celery application for fast api usage."""
        return cls._create_celery_app(name, config)

    @classmethod
    def _create_celery_app(
        cls,
        name: str,
        config: Config,
        include: Optional[Sequence[str]] = None,
    ):
        """Create a Celery application."""
        if include is None:
            include = []
        celery_app = Celery(name, task_cls=DishkaTask, include=include)
        celery_app.config_from_object(config.celery_config)
        celery_app.set_default()
        return celery_app
