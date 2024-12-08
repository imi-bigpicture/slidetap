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

from typing import Dict, Iterable, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, attribute_keyed_dict

from slidetap.database.db import DbBase, db
from slidetap.database.schema.item_schema import (
    DatabaseAnnotationSchema,
    DatabaseAnnotationToImageRelation,
    DatabaseImageSchema,
    DatabaseImageToSampleRelation,
    DatabaseItemSchema,
    DatabaseObservationSchema,
    DatabaseObservationToAnnotationRelation,
    DatabaseObservationToImageRelation,
    DatabaseObservationToSampleRelation,
    DatabaseSampleSchema,
    DatabaseSampleToSampleRelation,
)
from slidetap.database.schema.project_schema import DatabaseProjectSchema
from slidetap.model.schema.project_schema import ProjectSchema
from slidetap.model.schema.root_schema import RootSchema

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


class DatabaseRootSchema(DbBase):
    """A schema defines the sample, image, annotation, and
    observation types that can be included in metadata."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    project: Mapped[DatabaseProjectSchema] = db.relationship(
        DatabaseProjectSchema,
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
    )  # type: ignore
    samples: Mapped[Dict[str, DatabaseSampleSchema]] = db.relationship(
        DatabaseSampleSchema,
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
        collection_class=attribute_keyed_dict("name"),
    )  # type: ignore
    images: Mapped[Dict[str, DatabaseImageSchema]] = db.relationship(
        DatabaseImageSchema,
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
        collection_class=attribute_keyed_dict("name"),
    )  # type: ignore
    annotations: Mapped[Dict[str, DatabaseAnnotationSchema]] = db.relationship(
        DatabaseAnnotationSchema,
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
        collection_class=attribute_keyed_dict("name"),
    )  # type: ignore
    observations: Mapped[Dict[str, DatabaseObservationSchema]] = db.relationship(
        DatabaseObservationSchema,
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
        collection_class=attribute_keyed_dict("name"),
    )  # type: ignore

    __tablename__ = "root_schema"

    def __init__(
        self,
        uid: UUID,
        name: str,
        project: DatabaseProjectSchema,
        samples: Dict[str, DatabaseItemSchema],
        images: Dict[str, DatabaseItemSchema],
        annotations: Dict[str, DatabaseItemSchema],
        observations: Dict[str, DatabaseItemSchema],
    ):
        """Add a new schema to the database.

        Parameters
        ----------
        id: UUID
            Identifier for the schema
        name: str
            The name for the schema.
        """
        super().__init__(
            uid=uid,
            name=name,
            project=project,
            samples=samples,
            images=images,
            annotations=annotations,
            observations=observations,
            add=True,
            commit=True,
        )

    @property
    def model(self) -> RootSchema:
        return RootSchema(
            uid=self.uid,
            name=self.name,
            project=self.project.model,
            samples={name: item.model for name, item in self.samples.items()},
            images={name: item.model for name, item in self.images.items()},
            annotations={name: item.model for name, item in self.annotations.items()},
            observations={name: item.model for name, item in self.observations.items()},
        )

    @property
    def items(self) -> Iterable[DatabaseItemSchema]:
        return (
            item
            for item_type in [
                self.samples.values(),
                self.images.values(),
                self.annotations.values(),
                self.observations.values(),
            ]
            for item in item_type
        )

    @classmethod
    def get_or_create_from_model(cls, model: RootSchema) -> "DatabaseRootSchema":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        samples = {
            name: DatabaseItemSchema.get_or_create_from_model(item)
            for name, item in model.samples.items()
        }
        images = {
            name: DatabaseItemSchema.get_or_create_from_model(item)
            for name, item in model.images.items()
        }
        annotations = {
            name: DatabaseItemSchema.get_or_create_from_model(item)
            for name, item in model.annotations.items()
        }
        observations = {
            name: DatabaseItemSchema.get_or_create_from_model(item)
            for name, item in model.observations.items()
        }
        for sample in model.samples.values():
            for relation in sample.parents:
                DatabaseSampleToSampleRelation.ensure(relation)
        for image in model.images.values():
            for relation in image.samples:
                DatabaseImageToSampleRelation.from_model(relation)
        for annotation in model.annotations.values():
            for relation in annotation.images:
                DatabaseAnnotationToImageRelation.ensure(relation)
        for observation in model.observations.values():
            for relation in observation.samples:
                DatabaseObservationToSampleRelation.ensure(relation)
            for relation in observation.images:
                DatabaseObservationToImageRelation.ensure(relation)
            for relation in observation.annotations:
                DatabaseObservationToAnnotationRelation.ensure(relation)

        return DatabaseRootSchema(
            uid=model.uid,
            name=model.name,
            project=DatabaseProjectSchema.get_or_create_from_model(model.project),
            samples=samples,
            images=images,
            annotations=annotations,
            observations=observations,
        )

    @classmethod
    def get(cls, uid: UUID) -> "DatabaseRootSchema":
        schema = db.session.get(cls, uid)
        if schema is None:
            raise ValueError(f"Schema with uid {uid} not found.")
        return schema

    @classmethod
    def get_optional(cls, uid: UUID) -> Optional["DatabaseRootSchema"]:
        return db.session.get(cls, uid)

    @classmethod
    def get_for_project_schema(
        cls, project_schema: Union[UUID, DatabaseProjectSchema, ProjectSchema]
    ):
        if isinstance(project_schema, UUID):
            project_schema = DatabaseProjectSchema.get(project_schema)
        elif isinstance(project_schema, ProjectSchema):
            project_schema = DatabaseProjectSchema.get(project_schema.uid)
        return db.session.query(cls).filter(cls.project == project_schema).one()
