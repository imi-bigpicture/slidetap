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

"""Item schemas define Items (e.g. Sample) with attributes and parents"""

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, attribute_keyed_dict, mapped_column

from slidetap.database.db import DbBase, db
from slidetap.database.schema.attribute_schema import DatabaseAttributeSchema

# from slidetap.database.schema.root_schema import DatabaseRootSchema
from slidetap.model import ItemValueType
from slidetap.model.schema.item_relation import ItemRelation, ItemSchemaReference
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    AnnotationToImageRelation,
    ImageSchema,
    ImageToSampleRelation,
    ItemSchema,
    ObservationSchema,
    ObservationToAnnotationRelation,
    ObservationToImageRelation,
    ObservationToSampleRelation,
    SampleSchema,
    SampleToSampleRelation,
)

DatabaseItemSchemaType = TypeVar("DatabaseItemSchemaType", bound="DatabaseItemSchema")


class ItemRelationType(Enum):
    SAMPLE_TO_SAMPLE = 1
    IMAGE_TO_SAMPLE = 2
    ANNOTATION_TO_IMAG = 3
    OBSERVATION_TO_SAMPLE = 4
    OBSERVATION_TO_IMAGE = 5
    OBSERVARTION_TO_ANNOTATION = 6


class DatabaseItemRelation(DbBase):
    """Defines a relationship between two item schema types."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    description: Mapped[Optional[str]] = db.Column(db.String(512))
    relation_type: Mapped[ItemRelationType] = db.Column(db.Enum(ItemRelationType))

    __tablename__ = "item_relation"
    __mapper_args__ = {
        "polymorphic_on": "relation_type",
    }

    @property
    @abstractmethod
    def model(self) -> ItemRelation:
        raise NotImplementedError()

    @classmethod
    def from_model(cls, model: ItemRelation) -> "DatabaseItemRelation":
        raise NotImplementedError()

    @classmethod
    def ensure(cls, model: ItemRelation) -> None:
        existing = cls.query.get(model.uid)
        if existing is not None:
            return
        cls.from_model(model)


class DatabaseSampleToSampleRelation(DatabaseItemRelation):
    """Defines a relationship between two sample schema types."""

    parent_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("item_schema.uid"))
    child_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("item_schema.uid"))
    min_parents: Mapped[Optional[int]] = db.Column(db.Integer())
    max_parents: Mapped[Optional[int]] = db.Column(db.Integer())
    min_children: Mapped[Optional[int]] = db.Column(db.Integer())
    max_children: Mapped[Optional[int]] = db.Column(db.Integer())
    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.SAMPLE_TO_SAMPLE,
    }
    parent: Mapped["DatabaseSampleSchema"] = db.relationship(
        "DatabaseSampleSchema",
        foreign_keys=[parent_uid],
        back_populates="children",
    )  # type: ignore

    child: Mapped["DatabaseSampleSchema"] = db.relationship(
        "DatabaseSampleSchema",
        foreign_keys=[child_uid],
        back_populates="parents",
    )  # type: ignore

    def __init__(
        self,
        uid: UUID,
        name: str,
        parent: "DatabaseSampleSchema",
        child: "DatabaseSampleSchema",
        min_parents: Optional[int] = None,
        max_parents: Optional[int] = None,
        min_children: Optional[int] = None,
        max_children: Optional[int] = None,
        description: Optional[str] = None,
    ):
        """Create a new sample to sample relation.

        Parameters
        ----------
        name: str
            The name of the relation.
        parent: SampleSchema
            The parent sample schema.
        child: SampleSchema
            The child sample schema.
        min_parents: Optional[int] = None
            The minimum number of parents.
        max_parents: Optional[int] = None
            The maximum number of parents.
        min_children: Optional[int] = None
            The minimum number of children.
        max_children: Optional[int] = None
            The maximum number of children.
        description: Optional[str] = None
            The description of the relation.
        """
        self.child = child
        self.parent = parent
        self.min_children = min_children
        self.max_children = max_children
        self.min_parents = min_parents
        self.max_parents = max_parents
        super().__init__(
            uid=uid,
            add=True,
            commit=True,
            name=name,
            description=description,
        )

    @property
    def model(self) -> SampleToSampleRelation:
        current_app.logger.info(f"DatabaseSampleToSampleRelation.model, {self.uid}")
        return SampleToSampleRelation(
            uid=self.uid,
            name=self.name,
            description=self.description,
            parent=self.parent.reference,
            child=self.child.reference,
            min_parents=self.min_parents,
            max_parents=self.max_parents,
            min_children=self.min_children,
            max_children=self.max_children,
        )

    @classmethod
    def from_model(
        cls, model: SampleToSampleRelation
    ) -> "DatabaseSampleToSampleRelation":
        return cls(
            uid=model.uid,
            name=model.name,
            parent=DatabaseSampleSchema.get(model.parent.uid),
            child=DatabaseSampleSchema.get(model.child.uid),
            min_parents=model.min_parents,
            max_parents=model.max_parents,
            min_children=model.min_children,
            max_children=model.max_children,
            description=model.description,
        )


class DatabaseImageToSampleRelation(DatabaseItemRelation):
    """Defines a relationship between an image and a sample schema type."""

    image_to_sample_image_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )
    image_to_sample_sample_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.IMAGE_TO_SAMPLE,
    }
    image: Mapped["DatabaseImageSchema"] = db.relationship(
        "DatabaseImageSchema",
        foreign_keys=[image_to_sample_image_uid],
        back_populates="samples",
    )  # type: ignore

    sample: Mapped["DatabaseSampleSchema"] = db.relationship(
        "DatabaseSampleSchema",
        foreign_keys=[image_to_sample_sample_uid],
        back_populates="images",
    )  # type: ignore

    def __init__(
        self,
        uid: UUID,
        name: str,
        image: "DatabaseImageSchema",
        sample: "DatabaseSampleSchema",
        description: Optional[str] = None,
    ):
        """Create a new image to sample relation.

        Parameters
        ----------
        name: str
            The name of the relation.
        image: ImageSchema
            The image schema.
        sample: SampleSchema
            The sample schema.
        description: Optional[str] = None
            The description of the relation.
        """
        self.image = image
        self.sample = sample
        super().__init__(
            uid=uid, add=True, commit=True, name=name, description=description
        )

    @property
    def model(self) -> ImageToSampleRelation:
        return ImageToSampleRelation(
            uid=self.uid,
            name=self.name,
            description=self.description,
            image=self.image.reference,
            sample=self.sample.reference,
        )

    @classmethod
    def from_model(
        cls, model: ImageToSampleRelation
    ) -> "DatabaseImageToSampleRelation":
        return cls(
            uid=model.uid,
            name=model.name,
            image=DatabaseImageSchema.get(model.image.uid),
            sample=DatabaseSampleSchema.get(model.sample.uid),
            description=model.description,
        )


class DatabaseAnnotationToImageRelation(DatabaseItemRelation):
    """Defines a relationship between an annotation and a image schema type."""

    annotation_to_image_image_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )
    annotation_to_image_annotation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.ANNOTATION_TO_IMAG,
    }
    annotation: Mapped["DatabaseAnnotationSchema"] = db.relationship(
        "DatabaseAnnotationSchema",
        foreign_keys=[annotation_to_image_annotation_uid],
        back_populates="images",
    )  # type: ignore
    image: Mapped["DatabaseImageSchema"] = db.relationship(
        "DatabaseImageSchema",
        foreign_keys=[annotation_to_image_image_uid],
        back_populates="annotations",
    )  # type: ignore

    def __init__(
        self,
        uid: UUID,
        name: str,
        annotation: "DatabaseAnnotationSchema",
        image: "DatabaseImageSchema",
        description: Optional[str] = None,
    ):
        """Create a new annotation to image relation.

        Parameters
        ----------
        name: str
            The name of the relation.
        annotation: AnnotationSchema
            The sample schema.
        image: ImageSchema
            The image schema.
        description: Optional[str] = None
            The description of the relation.
        """
        self.annotation = annotation
        self.image = image
        super().__init__(
            uid=uid, add=True, commit=True, name=name, description=description
        )

    @property
    def model(self) -> AnnotationToImageRelation:
        return AnnotationToImageRelation(
            uid=self.uid,
            name=self.name,
            description=self.description,
            annotation=self.annotation.reference,
            image=self.image.reference,
        )

    @classmethod
    def from_model(
        cls, model: AnnotationToImageRelation
    ) -> "DatabaseAnnotationToImageRelation":
        return cls(
            uid=model.uid,
            name=model.name,
            annotation=DatabaseAnnotationSchema.get(model.annotation.uid),
            image=DatabaseImageSchema.get(model.image.uid),
            description=model.description,
        )


class DatabaseObservationToSampleRelation(DatabaseItemRelation):
    """Defines a relationship between an observation and a sample schema type."""

    observation_to_sample_observation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )
    observation_to_sample_sample_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.OBSERVATION_TO_SAMPLE,
    }
    observation: Mapped["DatabaseObservationSchema"] = db.relationship(
        "DatabaseObservationSchema",
        foreign_keys=[observation_to_sample_observation_uid],
        back_populates="samples",
    )  # type: ignore
    sample: Mapped["DatabaseSampleSchema"] = db.relationship(
        "DatabaseSampleSchema",
        foreign_keys=[observation_to_sample_sample_uid],
        back_populates="observations",
    )  # type: ignore

    def __init__(
        self,
        uid: UUID,
        name: str,
        observation: "DatabaseObservationSchema",
        sample: "DatabaseSampleSchema",
        description: Optional[str] = None,
    ):
        """Create a new observation to sample relation.

        Parameters
        ----------
        name: str
            The name of the relation.
        observation: ObservationSchema
            The observation schema.
        sample: SampleSchema
            The sample schema.
        description: Optional[str] = None
            The description of the relation.
        """
        self.observation = observation
        self.sample = sample
        super().__init__(
            uid=uid, add=True, commit=True, name=name, description=description
        )

    @property
    def model(self) -> ObservationToSampleRelation:
        return ObservationToSampleRelation(
            uid=self.uid,
            name=self.name,
            description=self.description,
            observation=self.observation.reference,
            sample=self.sample.reference,
        )

    @classmethod
    def from_model(
        cls, model: ObservationToSampleRelation
    ) -> "DatabaseObservationToSampleRelation":
        return cls(
            uid=model.uid,
            name=model.name,
            observation=DatabaseObservationSchema.get(model.observation.uid),
            sample=DatabaseSampleSchema.get(model.sample.uid),
            description=model.description,
        )


class DatabaseObservationToImageRelation(DatabaseItemRelation):
    """Defines a relationship between an observation and a image schema type."""

    observation_to_image_observation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )
    observation_to_image_image_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.OBSERVATION_TO_IMAGE,
    }
    observation: Mapped["DatabaseObservationSchema"] = db.relationship(
        "DatabaseObservationSchema",
        foreign_keys=[observation_to_image_observation_uid],
        back_populates="images",
    )  # type: ignore
    image: Mapped["DatabaseImageSchema"] = db.relationship(
        "DatabaseImageSchema",
        foreign_keys=[observation_to_image_image_uid],
        back_populates="observations",
    )  # type: ignore

    def __init__(
        self,
        uid: UUID,
        name: str,
        observation: "DatabaseObservationSchema",
        image: "DatabaseImageSchema",
        description: Optional[str] = None,
    ):
        """Create a new observation to image relation.

        Parameters
        ----------
        name: str
            The name of the relation.
        observation: ObservationSchema
            The observation schema.
        image: ImageSchema
            The image schema.
        description: Optional[str] = None
            The description of the relation.
        """
        self.observation = observation
        self.image = image
        super().__init__(
            uid=uid, add=True, commit=True, name=name, description=description
        )

    @property
    def model(self) -> ObservationToImageRelation:
        return ObservationToImageRelation(
            uid=self.uid,
            name=self.name,
            description=self.description,
            observation=self.observation.reference,
            image=self.image.reference,
        )

    @classmethod
    def from_model(
        cls, model: ObservationToImageRelation
    ) -> "DatabaseObservationToImageRelation":
        return cls(
            uid=model.uid,
            name=model.name,
            observation=DatabaseObservationSchema.get(model.observation.uid),
            image=DatabaseImageSchema.get(model.image.uid),
            description=model.description,
        )


class DatabaseObservationToAnnotationRelation(DatabaseItemRelation):
    """Defines a relationship between an observation and a annotation schema type."""

    observation_to_annotation_observation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )
    observation_to_annotation_annotation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.OBSERVARTION_TO_ANNOTATION,
    }
    observation: Mapped["DatabaseObservationSchema"] = db.relationship(
        "DatabaseObservationSchema",
        foreign_keys=[observation_to_annotation_observation_uid],
        back_populates="annotations",
    )  # type: ignore
    annotation: Mapped["DatabaseAnnotationSchema"] = db.relationship(
        "DatabaseAnnotationSchema",
        foreign_keys=[observation_to_annotation_annotation_uid],
        back_populates="observations",
    )  # type: ignore

    def __init__(
        self,
        uid: UUID,
        name: str,
        observation: "DatabaseObservationSchema",
        annotation: "DatabaseAnnotationSchema",
        description: Optional[str] = None,
    ):
        """Create a new observation to annotation relation.

        Parameters
        ----------
        observation: ObservationSchema
            The observation schema.
        annotation: AnnotationSchema
            The annotation schema.
        """
        self.observation = observation
        self.annotation = annotation
        super().__init__(
            uid=uid, add=True, commit=True, name=name, description=description
        )

    @property
    def model(self) -> ObservationToAnnotationRelation:
        return ObservationToAnnotationRelation(
            uid=self.uid,
            name=self.name,
            description=self.description,
            observation=self.observation.reference,
            annotation=self.annotation.reference,
        )

    @classmethod
    def from_model(
        cls, model: ObservationToAnnotationRelation
    ) -> "DatabaseObservationToAnnotationRelation":
        return cls(
            uid=model.uid,
            name=model.name,
            observation=DatabaseObservationSchema.get(model.observation.uid),
            annotation=DatabaseAnnotationSchema.get(model.annotation.uid),
            description=model.description,
        )


ItemSchemaType = TypeVar("ItemSchemaType", bound=ItemSchema)


class DatabaseItemSchema(DbBase, Generic[ItemSchemaType]):
    """A type of item that are included in a schema."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    display_name: Mapped[str] = db.Column(db.String(128))
    item_value_type: Mapped[ItemValueType] = db.Column(db.Enum(ItemValueType))
    display_order: Mapped[int] = db.Column(db.Integer())

    attributes: Mapped[Dict[str, DatabaseAttributeSchema]] = db.relationship(
        DatabaseAttributeSchema,
        collection_class=attribute_keyed_dict("tag"),
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
    )  # type: ignore

    # schema: Mapped[DatabaseRootSchema] = db.relationship(DatabaseRootSchema, cascade="all, delete")  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("root_schema.uid"))

    __mapper_args__ = {
        "polymorphic_on": "item_value_type",
    }
    __tablename__ = "item_schema"
    # __table_args__ = (db.UniqueConstraint("schema_uid", "name"),)

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        display_order: int,
        attributes: Optional[Dict[str, DatabaseAttributeSchema]] = None,
    ):
        """Add a new schema item type to the database.

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
            name=name,
            display_name=display_name,
            display_order=display_order,
            add=True,
            commit=True,
        )

    @classmethod
    def get_or_create_from_model(cls, model: ItemSchema) -> "DatabaseItemSchema":
        if isinstance(model, SampleSchema):
            return DatabaseSampleSchema.get_or_create_from_model(model)
        if isinstance(model, ImageSchema):
            return DatabaseImageSchema.get_or_create_from_model(model)
        if isinstance(model, AnnotationSchema):
            return DatabaseAnnotationSchema.get_or_create_from_model(model)
        if isinstance(model, ObservationSchema):
            return DatabaseObservationSchema.get_or_create_from_model(model)
        raise ValueError(f"Unknown item schema type {model}")

    # @classmethod
    # def get_for_schema(
    #     cls: Type[DatabaseItemSchemaType], schema: Union[DatabaseRootSchema, UUID]
    # ) -> Iterable[DatabaseItemSchemaType]:
    #     if isinstance(schema, DatabaseRootSchema):
    #         schema = schema.uid
    #     return db.session.scalars(
    #         select(cls).filter_by(schema_uid=schema).order_by(cls.display_order)
    #     )

    # @classmethod
    # def get(
    #     cls: Type[DatabaseItemSchemaType],
    #     schema: Union[DatabaseRootSchema, UUID],
    #     name: str,
    # ) -> DatabaseItemSchemaType:
    #     if isinstance(schema, DatabaseRootSchema):
    #         schema = schema.uid
    #     return db.session.scalars(
    #         select(cls).filter_by(schema_uid=schema, name=name)
    #     ).one()

    # @classmethod
    # def get_optional(
    #     cls: Type[DatabaseItemSchemaType],
    #     schema: Union[DatabaseRootSchema, UUID],
    #     name: str,
    # ) -> Optional[DatabaseItemSchemaType]:
    #     if isinstance(schema, DatabaseRootSchema):
    #         schema = schema.uid
    #     return db.session.scalars(
    #         select(cls).filter_by(schema_uid=schema, name=name)
    #     ).one_or_none()

    @classmethod
    def get(cls: Type[DatabaseItemSchemaType], uid: UUID) -> DatabaseItemSchemaType:
        schema = cls.query.get(uid)
        if schema is None:
            raise ValueError(f"Item schema with uid {uid} not found")
        return schema

    @classmethod
    def get_optional(
        cls: Type[DatabaseItemSchemaType], uid: UUID
    ) -> Optional[DatabaseItemSchemaType]:
        return cls.query.get(uid)

    @property
    @abstractmethod
    def model(self) -> ItemSchemaType:
        raise NotImplementedError()

    @property
    def reference(self) -> ItemSchemaReference:
        return ItemSchemaReference(
            uid=self.uid,
            name=self.name,
            display_name=self.display_name,
        )


class DatabaseObservationSchema(DatabaseItemSchema):
    """A schema item type for observations."""

    # uid: Mapped[UUID] = mapped_column(
    #     db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    # )

    samples: Mapped[List[DatabaseObservationToSampleRelation]] = db.relationship(
        DatabaseObservationToSampleRelation,
        back_populates="observation",
        foreign_keys=[
            DatabaseObservationToSampleRelation.observation_to_sample_observation_uid
        ],
    )  # type: ignore
    images: Mapped[List[DatabaseObservationToImageRelation]] = db.relationship(
        DatabaseObservationToImageRelation,
        back_populates="observation",
        foreign_keys=[
            DatabaseObservationToImageRelation.observation_to_image_observation_uid
        ],
    )  # type: ignore
    annotations: Mapped[
        List[DatabaseObservationToAnnotationRelation]
    ] = db.relationship(
        DatabaseObservationToAnnotationRelation,
        back_populates="observation",
        foreign_keys=[
            DatabaseObservationToAnnotationRelation.observation_to_annotation_observation_uid
        ],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.OBSERVATION,
    }
    # __tablename__ = "observation_schema"

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        display_order: int,
        annotations: Optional[List[DatabaseObservationToAnnotationRelation]] = None,
        images: Optional[List[DatabaseObservationToImageRelation]] = None,
        samples: Optional[List[DatabaseObservationToSampleRelation]] = None,
        attributes: Optional[Dict[str, DatabaseAttributeSchema]] = None,
    ):
        """Add a new observation schema item type to the database.

        Parameters
        ----------
        schema: Schema
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[Sequence[str]] = None,
            Attributes that the item type can have.
        """
        self.annotations = annotations or []
        self.images = images or []
        self.samples = samples or []
        super().__init__(
            uid=uid,
            name=name,
            display_name=display_name,
            display_order=display_order,
            attributes=attributes,
        )

    @classmethod
    def get_or_create_from_model(
        cls, model: ObservationSchema
    ) -> "DatabaseObservationSchema":
        existing = cls.query.get(model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            display_order=model.display_order,
            attributes={
                attribute.tag: DatabaseAttributeSchema.get_or_create_from_model(
                    attribute
                )
                for attribute in model.attributes.values()
            },
        )

    @property
    def model(self) -> ObservationSchema:
        return ObservationSchema(
            uid=self.uid,
            name=self.name,
            display_name=self.display_name,
            display_order=self.display_order,
            attributes={
                tag: attribute.model for tag, attribute in self.attributes.items()
            },
            samples=tuple([sample.model for sample in self.samples]),
            images=tuple([image.model for image in self.images]),
            annotations=tuple([annotation.model for annotation in self.annotations]),
        )


class DatabaseAnnotationSchema(DatabaseItemSchema):
    """A schema item type for annotations."""

    # uid: Mapped[UUID] = mapped_column(
    #     db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    # )

    images: Mapped[List[DatabaseAnnotationToImageRelation]] = db.relationship(
        DatabaseAnnotationToImageRelation,
        back_populates="annotation",
        foreign_keys=[
            DatabaseAnnotationToImageRelation.annotation_to_image_annotation_uid
        ],
    )  # type: ignore

    observations: Mapped[
        List[DatabaseObservationToAnnotationRelation]
    ] = db.relationship(
        DatabaseObservationToAnnotationRelation,
        back_populates="annotation",
        foreign_keys=[
            DatabaseObservationToAnnotationRelation.observation_to_annotation_annotation_uid
        ],
    )  # type: ignore
    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.ANNOTATION,
    }
    # __tablename__ = "annotation_schema"

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        display_order: int,
        images: Optional[List[DatabaseAnnotationToImageRelation]] = None,
        attributes: Optional[Dict[str, DatabaseAttributeSchema]] = None,
    ):
        """Add a new annotation schema item type to the database.

        Parameters
        ----------
        schema: Schema
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[Sequence[str]] = None
            Attributes that the item type can have.
        """
        self.images = [
            DatabaseAnnotationToImageRelation(
                image.uid, image.name, self, image.image, image.description
            )
            for image in images or []
        ] or []  # type: ignore

        super().__init__(
            uid=uid,
            name=name,
            display_name=display_name,
            display_order=display_order,
            attributes=attributes,
        )

    @classmethod
    def get_or_create_from_model(
        cls, model: AnnotationSchema
    ) -> "DatabaseAnnotationSchema":
        existing = cls.query.get(model.uid)

        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            display_order=model.display_order,
            attributes={
                attribute.tag: DatabaseAttributeSchema.get_or_create_from_model(
                    attribute
                )
                for attribute in model.attributes.values()
            },
        )

    @property
    def model(self) -> AnnotationSchema:
        return AnnotationSchema(
            uid=self.uid,
            name=self.name,
            display_name=self.display_name,
            display_order=self.display_order,
            attributes={
                tag: attribute.model for tag, attribute in self.attributes.items()
            },
            images=tuple(image.model for image in self.images),
            oberservations=tuple(
                observation.model for observation in self.observations
            ),
        )


class DatabaseImageSchema(DatabaseItemSchema):
    """A schema item type for images."""

    # uid: Mapped[UUID] = mapped_column(
    #     db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    # )

    samples: Mapped[List[DatabaseImageToSampleRelation]] = db.relationship(
        DatabaseImageToSampleRelation,
        back_populates="image",
        foreign_keys=[DatabaseImageToSampleRelation.image_to_sample_image_uid],
    )  # type: ignore

    annotations: Mapped[List[DatabaseAnnotationToImageRelation]] = db.relationship(
        DatabaseAnnotationToImageRelation,
        back_populates="image",
        foreign_keys=[DatabaseAnnotationToImageRelation.annotation_to_image_image_uid],
    )  # type: ignore
    observations: Mapped[List[DatabaseObservationToImageRelation]] = db.relationship(
        DatabaseObservationToImageRelation,
        back_populates="image",
        foreign_keys=[
            DatabaseObservationToImageRelation.observation_to_image_image_uid
        ],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.IMAGE,
    }
    # __tablename__ = "image_schema"

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        display_order: int,
        samples: Optional[List[DatabaseImageToSampleRelation]] = None,
        attributes: Optional[Dict[str, DatabaseAttributeSchema]] = None,
    ):
        """Add a new image schema item type to the database.

        Parameters
        ----------
        schema: Schema
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[Sequence[str]] = None
            Attributes that the item type can have.
        """
        self.samples = samples or []
        super().__init__(
            uid=uid,
            name=name,
            display_name=display_name,
            display_order=display_order,
            attributes=attributes,
        )

    @classmethod
    def get_or_create_from_model(cls, model: ImageSchema) -> "DatabaseImageSchema":
        existing = cls.query.get(model.uid)

        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            display_order=model.display_order,
            attributes={
                attribute.tag: DatabaseAttributeSchema.get_or_create_from_model(
                    attribute
                )
                for attribute in model.attributes.values()
            },
        )

    @property
    def model(self) -> ImageSchema:
        return ImageSchema(
            uid=self.uid,
            name=self.name,
            display_name=self.display_name,
            display_order=self.display_order,
            attributes={
                tag: attribute.model for tag, attribute in self.attributes.items()
            },
            samples=tuple(sample.model for sample in self.samples),
            annotations=tuple(annotation.model for annotation in self.annotations),
            observations=tuple(observation.model for observation in self.observations),
        )


class DatabaseSampleSchema(DatabaseItemSchema):
    """A schema item type for samples."""

    # uid: Mapped[UUID] = mapped_column(
    #     db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    # )

    # Relationships
    parents: Mapped[List[DatabaseSampleToSampleRelation]] = db.relationship(
        DatabaseSampleToSampleRelation,
        cascade="all, delete",
        back_populates="child",
        foreign_keys=[DatabaseSampleToSampleRelation.child_uid],
    )  # type: ignore

    children: Mapped[List[DatabaseSampleToSampleRelation]] = db.relationship(
        DatabaseSampleToSampleRelation,
        cascade="all, delete",
        back_populates="parent",
        foreign_keys=[DatabaseSampleToSampleRelation.parent_uid],
    )  # type: ignore

    images: Mapped[List[DatabaseImageToSampleRelation]] = db.relationship(
        DatabaseImageToSampleRelation,
        back_populates="sample",
        foreign_keys=[DatabaseImageToSampleRelation.image_to_sample_sample_uid],
    )  # type: ignore

    observations: Mapped[List[DatabaseObservationToSampleRelation]] = db.relationship(
        DatabaseObservationToSampleRelation,
        back_populates="sample",
        foreign_keys=[
            DatabaseObservationToSampleRelation.observation_to_sample_sample_uid
        ],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.SAMPLE,
    }
    # __tablename__ = "sample_schema"

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        display_order: int,
        children: Optional[List[DatabaseSampleToSampleRelation]] = None,
        attributes: Optional[Dict[str, DatabaseAttributeSchema]] = None,
    ):
        self.children = [
            DatabaseSampleToSampleRelation(
                relation.uid,
                relation.name,
                self,
                relation.child,
                relation.min_parents,
                relation.max_parents,
                relation.min_children,
                relation.max_children,
                relation.description,
            )
            for relation in children or []
        ]  # type: ignore
        self.parents = []
        super().__init__(
            uid=uid,
            name=name,
            display_name=display_name,
            display_order=display_order,
            attributes=attributes,
        )

    @classmethod
    def get_or_create_from_model(cls, model: SampleSchema) -> "DatabaseSampleSchema":
        existing = cls.query.get(model.uid)

        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            display_order=model.display_order,
            attributes={
                attribute.tag: DatabaseAttributeSchema.get_or_create_from_model(
                    attribute
                )
                for attribute in model.attributes.values()
            },
        )

    @property
    def model(self) -> SampleSchema:
        return SampleSchema(
            uid=self.uid,
            name=self.name,
            display_name=self.display_name,
            display_order=self.display_order,
            attributes={
                tag: attribute.model for tag, attribute in self.attributes.items()
            },
            children=tuple(child.model for child in self.children),
            parents=tuple(parent.model for parent in self.parents),
            images=tuple(image.model for image in self.images),
            observations=tuple(observation.model for observation in self.observations),
        )
