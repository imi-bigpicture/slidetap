"""Metaclass for exporter."""
from abc import ABCMeta
from typing import Optional

from flask import Flask

from slidetap.flask_extension import FlaskExtension
from slidetap.storage.storage import Storage


class Exporter(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for an exporter. Has a Storage for storing exported images
    and metadata."""

    def __init__(self, storage: Storage, app: Optional[Flask] = None):
        self._storage = storage
        if app is not None:
            self.init_app(app)

    @property
    def storage(self) -> Storage:
        """The storage used for exporting images and metadata."""
        return self._storage
