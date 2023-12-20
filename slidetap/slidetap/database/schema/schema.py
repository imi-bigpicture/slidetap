from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped

from slidetap.database.db import DbBase, db

"""
A schema defines the structure of the metadata that can be used within a project. The
schema contains collections of (biological) sample types, image types, observation
types, annotation types. Most types are of the HierarchicItemSchema that can be
structured into a hierarchy by relationships, for example:
- `Biological being` -> `Specimen` -> `Block` -> `Slide`.
The relation ship is set by the parents and children properties. A type can have multiple
parents or children, for example a `Biological being` can have child types `Case` and
`Specimen`. `Specimen` can have parent types `Biological being` and `Case`. A type can
also have a parent of a different type class, for example the parents of an `Image`
class type are of the `Sample` class.

The properties a type can have is defined a list of attributes names and
a dictionary of attribute object schema types. A attribute object schema types defines
a more complex attribute that can in it self contain attribute object schema types.

"""


class Schema(DbBase):
    """A schema defines the sample, image, annotation, and
    observation types that can be included in metadata."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))

    def __init__(self, uid: UUID, name: str):
        """Add a new schema to the database.

        Parameters
        ----------
        id: UUID
            Identifier for the schema
        name: str
            The name for the schema.
        """
        super().__init__(uid=uid, name=name, add=True, commit=True)

    @classmethod
    def get_or_create(cls, uid: UUID, name: str) -> "Schema":
        """Get or create schema with id.

        Parameters
        ----------
        uid: UUID
            Identifier for the schema
        name: str
            The name for the schema.

        Returns
        ----------
        Schema
            Existing or new schema.
        """
        schema = cls.get(uid)
        if schema is None:
            schema = cls(uid, name)
        return schema

    @classmethod
    def get(cls, uid: UUID) -> Optional["Schema"]:
        return db.session.get(cls, uid)
