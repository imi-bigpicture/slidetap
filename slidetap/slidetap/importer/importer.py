"""Metaclass for importer."""
from abc import ABCMeta
from typing import Optional

from flask import Blueprint, Flask
from slidetap.database.project import Project
from slidetap.flask_extension import FlaskExtension


class Importer(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for importer."""

    def __init__(self, app: Optional[Flask] = None):
        if app is not None:
            self.init_app(app)

    @property
    def blueprint(self) -> Optional[Blueprint]:
        """If importer have api endpoints they should be register
        to a blueprint and returned using this property."""
        return None

    def reset_project(self, project: Project):
        """Should reset any internally stored data for project."""
        pass
