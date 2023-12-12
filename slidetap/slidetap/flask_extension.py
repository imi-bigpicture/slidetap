"""Metaclass for flask extensions."""
from abc import ABCMeta
from typing import Optional
from flask import Flask


class FlaskExtension(metaclass=ABCMeta):
    """Metaclass to use for classes that need to be initiated with the app."""

    def __init__(
        self,
        app: Optional[Flask] = None,
    ):
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initiate FlaskExtension with Flask-app."""
        pass
