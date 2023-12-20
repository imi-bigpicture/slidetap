from os import makedirs
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def setup_db(app: Flask):
    """Initiate db with app and create database tables."""
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if database_uri.startswith("sqlite") and (database_uri != "sqlite:///:memory:"):
        database_path = Path(database_uri.split("sqlite:///", 1)[1])
        makedirs(database_path.parent, exist_ok=True)
    db.init_app(app)
    db.create_all()


class NotFoundError(Exception):
    """Raised when item in database is not found."""

    def __init__(self, error: str):
        self.error = error

    def __str__(self) -> str:
        return self.error


class NotAllowedActionError(Exception):
    """Raised when action on item in database is not allowed."""

    def __init__(self, error: str):
        self.error = error

    def __str__(self) -> str:
        return self.error


class DbBase(db.Model):
    __abstract__ = True

    def __init__(self, add: bool, commit: bool, **kwargs):
        super().__init__(**kwargs)
        if add:
            db.session.add(self)
        if commit:
            db.session.commit()
