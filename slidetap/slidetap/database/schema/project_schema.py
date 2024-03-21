"""Project schema define Project with attributes"""

from typing import List, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped

from slidetap.database.db import DbBase, db
from slidetap.database.schema.attribute_schema import AttributeSchema
from slidetap.database.schema.schema import Schema


class ProjectSchema(DbBase):
    """A type of item that are included in a schema."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    display_name: Mapped[str] = db.Column(db.String(128))

    attributes: Mapped[List[AttributeSchema]] = db.relationship(
        AttributeSchema,
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
    )  # type: ignore

    schema: Mapped[Schema] = db.relationship(Schema, cascade="all, delete")  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("schema.uid"))

    __table_args__ = (db.UniqueConstraint("schema_uid"),)

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        attributes: Optional[List[AttributeSchema]] = None,
    ):
        """Add a new project schema to the database.

        Parameters
        ----------
        schema: Schema
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[Dict[str, Sequence[type]]] = None
            Attributes that the item type can have.
        """
        if attributes is not None:
            self.attributes = attributes

        super().__init__(
            add=True,
            commit=True,
            schema_uid=schema.uid,
            name=name,
            display_name=display_name,
        )

    @classmethod
    def get_for_schema(cls, schema: Union[UUID, Schema]) -> "ProjectSchema":
        if isinstance(schema, Schema):
            schema = schema.uid
        return db.session.scalars(select(cls).filter_by(schema_uid=schema)).one()

    @classmethod
    def get_optional_for_schema(
        cls, schema: Union[UUID, Schema]
    ) -> Optional["ProjectSchema"]:
        if isinstance(schema, Schema):
            schema = schema.uid
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema)
        ).one_or_none()

    @classmethod
    def get(cls, uid: UUID) -> Optional["ProjectSchema"]:
        return db.session.get(cls, uid)

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "ProjectSchema":
        project_schema = cls.get_optional_for_schema(schema.uid)
        if project_schema is None:
            project_schema = cls(schema, name, display_name, attributes)
        return project_schema
