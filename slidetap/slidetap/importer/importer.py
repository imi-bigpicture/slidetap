"""Metaclass for importer."""

from abc import ABCMeta
from typing import Optional

from flask import Blueprint, Flask

from slidetap.database.project import Project
from slidetap.flask_extension import FlaskExtension
from slidetap.scheduler import Scheduler


class Importer(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for importer."""

    def __init__(self, scheduler: Scheduler, app: Optional[Flask] = None):
        self._scheduler = scheduler
        super().__init__(app)

    def init_app(self, app: Flask):
        super().init_app(app)
        self._scheduler.init_app(app)

    @property
    def blueprint(self) -> Optional[Blueprint]:
        """If importer have api endpoints they should be register
        to a blueprint and returned using this property."""
        return None

    def reset_project(self, project: Project):
        """Should reset any internally stored data for project."""
        pass
