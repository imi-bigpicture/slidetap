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

from os import makedirs
from pathlib import Path

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import NullPool
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def setup_db(app: Flask):
    """Initiate db with app and create database tables."""
    current_app.logger.info("Setting up database")
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "poolclass": NullPool,
    }
    if database_uri.startswith("sqlite") and (database_uri != "sqlite:///:memory:"):
        database_path = Path(database_uri.split("sqlite:///", 1)[1])
        makedirs(database_path.parent, exist_ok=True)
    db.init_app(app)
    db.create_all()
    current_app.logger.info("Setting up database completed")
    return db


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
        if add and self not in db.session:
            # Try to add if not already in session
            try:
                db.session.add(self)
            except InvalidRequestError as excption:
                # Only raise if not already in session
                if self not in db.session:
                    raise excption
        if commit:
            db.session.commit()
