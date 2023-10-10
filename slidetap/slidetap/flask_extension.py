"""Metaclass for flask extensions."""
from abc import ABCMeta
from flask import Flask


class FlaskExtension(metaclass=ABCMeta):
    """Metaclass to use for classes that need to be initiated with the app."""

    def init_app(self, app: Flask):
        """Initiate FlaskExtension with Flask-app."""
        pass
