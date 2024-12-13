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

"""Project schema define Project with attributes"""

from typing import Dict, Iterable, Optional
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped, attribute_keyed_dict

from slidetap.database.db import DbBase, db
from slidetap.database.schema.attribute_schema import DatabaseAttributeSchema

# from slidetap.database.schema.root_schema import DatabaseRootSchema
from slidetap.model.schema.project_schema import ProjectSchema


class DatabaseProjectSchema(DbBase):
    """A type of item that are included in a schema."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    display_name: Mapped[str] = db.Column(db.String(128))

    attributes: Mapped[Dict[str, DatabaseAttributeSchema]] = db.relationship(
        DatabaseAttributeSchema,
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
        collection_class=attribute_keyed_dict("tag"),
    )  # type: ignore

    # root_schema: Mapped[DatabaseRootSchema] = db.relationship(DatabaseRootSchema, cascade="all, delete")  # type: ignore

    # For relations
    root_schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("root_schema.uid"))

    # __table_args__ = (db.UniqueConstraint("schema_uid"),)
    __tablename__ = "project_schema"

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        attributes: Optional[Dict[str, DatabaseAttributeSchema]] = None,
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
            uid=uid,
            add=True,
            commit=True,
            name=name,
            display_name=display_name,
        )

    @property
    def model(self) -> ProjectSchema:
        return ProjectSchema(
            uid=self.uid,
            name=self.name,
            display_name=self.display_name,
            attributes=(
                {tag: attribute.model for tag, attribute in self.attributes.items()}
            ),
        )

    @property
    def attribute_tags(self) -> Iterable[str]:
        return db.session.scalars(
            select(DatabaseAttributeSchema.tag).where(
                DatabaseAttributeSchema.project_schema_uid == self.uid
            )
        ).all()

    def get_attribute(self, tag: str) -> DatabaseAttributeSchema:
        return db.session.scalars(
            select(DatabaseAttributeSchema).filter_by(
                project_schema_uid=self.uid, tag=tag
            )
        ).one()

    def iterate_attributes(self) -> Iterable[DatabaseAttributeSchema]:
        return db.session.scalars(
            select(DatabaseAttributeSchema).where(
                DatabaseAttributeSchema.project_schema_uid == self.uid
            )
        )

    @classmethod
    def get(cls, uid: UUID) -> "DatabaseProjectSchema":
        schema = db.session.get(cls, uid)
        if schema is None:
            raise ValueError(f"Project schema with uid {uid} does not exist")
        return schema

    @classmethod
    def get_or_create_from_model(cls, model: ProjectSchema) -> "DatabaseProjectSchema":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return DatabaseProjectSchema(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            attributes={
                tag: DatabaseAttributeSchema.get_or_create_from_model(attribute)
                for tag, attribute in model.attributes.items()
            },
        )
