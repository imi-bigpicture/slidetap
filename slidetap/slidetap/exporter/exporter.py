"""Metaclass for exporter."""

from abc import ABCMeta
from typing import Optional

from flask import Flask

from slidetap.flask_extension import FlaskExtension
from slidetap.scheduler import Scheduler
from slidetap.storage.storage import Storage


class Exporter(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for an exporter. Has a Storage for storing exported images
    and metadata."""

    def __init__(
        self, scheduler: Scheduler, storage: Storage, app: Optional[Flask] = None
    ):
        self._scheduler = scheduler
        self._storage = storage
        super().__init__(app)

    @property
    def storage(self) -> Storage:
        """The storage used for exporting images and metadata."""
        return self._storage
