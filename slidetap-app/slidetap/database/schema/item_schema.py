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

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional, Sequence, Type, TypeVar, Union
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import DbBase, db
from slidetap.database.schema.attribute_schema import AttributeSchema
from slidetap.database.schema.schema import Schema
from slidetap.model import ItemValueType

ItemSchemaType = TypeVar("ItemSchemaType", bound="ItemSchema")


class ItemRelationType(Enum):
    SAMPLE_TO_SAMPLE = 1
    IMAGE_TO_SAMPLE = 2
    ANNOTATION_TO_IMAG = 3
    OBSERVATION_TO_SAMPLE = 4
    OBSERVATION_TO_IMAGE = 5
    OBSERVARTION_TO_ANNOTATION = 6


class ItemRelationDefinition:
    name: str
    description: Optional[str]


@dataclass
class SampleRelationDefinition(ItemRelationDefinition):
    name: str
    child: "SampleSchema"
    min_parents: Optional[int] = None
    max_parents: Optional[int] = None
    min_children: Optional[int] = None
    max_children: Optional[int] = None
    description: Optional[str] = None


@dataclass
class ImageRelationDefinition(ItemRelationDefinition):
    name: str
    sample: "SampleSchema"
    description: Optional[str] = None


@dataclass
class AnnotationRelationDefinition(ItemRelationDefinition):
    name: str
    image: "ImageSchema"
    description: Optional[str] = None


@dataclass
class ObservationRelationDefinition(ItemRelationDefinition):
    name: str
    item: Union["SampleSchema", "ImageSchema", "AnnotationSchema"]
    description: Optional[str] = None


class ItemRelation(DbBase):
    """Defines a relationship between two item schema types."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    description: Mapped[Optional[str]] = db.Column(db.String(512))
    relation_type: Mapped[ItemRelationType] = db.Column(db.Enum(ItemRelationType))

    __mapper_args__ = {
        "polymorphic_on": "relation_type",
    }


class SampleToSampleRelation(ItemRelation):
    """Defines a relationship between two sample schema types."""

    parent_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("sample_schema.uid"))
    child_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("sample_schema.uid"))
    min_parents: Mapped[Optional[int]] = db.Column(db.Integer())
    max_parents: Mapped[Optional[int]] = db.Column(db.Integer())
    min_children: Mapped[Optional[int]] = db.Column(db.Integer())
    max_children: Mapped[Optional[int]] = db.Column(db.Integer())
    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.SAMPLE_TO_SAMPLE,
    }
    parent: Mapped["SampleSchema"] = db.relationship(
        "SampleSchema",
        foreign_keys=[parent_uid],
        back_populates="children",
    )  # type: ignore

    child: Mapped["SampleSchema"] = db.relationship(
        "SampleSchema",
        foreign_keys=[child_uid],
        back_populates="parents",
    )  # type: ignore

    def __init__(
        self,
        name: str,
        parent: "SampleSchema",
        child: "SampleSchema",
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
            add=True,
            commit=True,
            name=name,
            description=description,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.uid} {self.name} {self.parent} {self.child}>"


class ImageToSampleRelation(ItemRelation):
    """Defines a relationship between an image and a sample schema type."""

    image_to_sample_image_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("image_schema.uid")
    )
    image_to_sample_sample_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("sample_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.IMAGE_TO_SAMPLE,
    }
    image: Mapped["ImageSchema"] = db.relationship(
        "ImageSchema",
        foreign_keys=[image_to_sample_image_uid],
        back_populates="samples",
    )  # type: ignore

    sample: Mapped["SampleSchema"] = db.relationship(
        "SampleSchema",
        foreign_keys=[image_to_sample_sample_uid],
        back_populates="images",
    )  # type: ignore

    def __init__(
        self,
        name: str,
        image: "ImageSchema",
        sample: "SampleSchema",
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
        super().__init__(add=True, commit=True, name=name, description=description)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.uid} {self.name} {self.image} {self.sample}>"


class AnnotationToImageRelation(ItemRelation):
    """Defines a relationship between an annotation and a image schema type."""

    annotation_to_image_image_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("image_schema.uid")
    )
    annotation_to_image_annotation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("annotation_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.ANNOTATION_TO_IMAG,
    }
    annotation: Mapped["AnnotationSchema"] = db.relationship(
        "AnnotationSchema",
        foreign_keys=[annotation_to_image_annotation_uid],
        back_populates="images",
    )  # type: ignore
    image: Mapped["ImageSchema"] = db.relationship(
        "ImageSchema",
        foreign_keys=[annotation_to_image_image_uid],
        back_populates="annotations",
    )  # type: ignore

    def __init__(
        self,
        name: str,
        annotation: "AnnotationSchema",
        image: "ImageSchema",
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
        super().__init__(add=True, commit=True, name=name, description=description)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.uid} {self.name} {self.annotation} {self.image}>"


class ObservationToSampleRelation(ItemRelation):
    """Defines a relationship between an observation and a sample schema type."""

    observation_to_sample_observation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("observation_schema.uid")
    )
    observation_to_sample_sample_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("sample_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.OBSERVATION_TO_SAMPLE,
    }
    observation: Mapped["ObservationSchema"] = db.relationship(
        "ObservationSchema",
        foreign_keys=[observation_to_sample_observation_uid],
        back_populates="samples",
    )  # type: ignore
    sample: Mapped["SampleSchema"] = db.relationship(
        "SampleSchema",
        foreign_keys=[observation_to_sample_sample_uid],
        back_populates="observations",
    )  # type: ignore

    def __init__(
        self,
        name: str,
        observation: "ObservationSchema",
        sample: "SampleSchema",
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
        super().__init__(add=True, commit=True, name=name, description=description)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.uid} {self.name} {self.observation} {self.sample}>"


class ObservationToImageRelation(ItemRelation):
    """Defines a relationship between an observation and a image schema type."""

    observation_to_image_observation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("observation_schema.uid")
    )
    observation_to_image_image_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("image_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.OBSERVATION_TO_IMAGE,
    }
    observation: Mapped["ObservationSchema"] = db.relationship(
        "ObservationSchema",
        foreign_keys=[observation_to_image_observation_uid],
        back_populates="images",
    )  # type: ignore
    image: Mapped["ImageSchema"] = db.relationship(
        "ImageSchema",
        foreign_keys=[observation_to_image_image_uid],
        back_populates="observations",
    )  # type: ignore

    def __init__(
        self,
        name: str,
        observation: "ObservationSchema",
        image: "ImageSchema",
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
        super().__init__(add=True, commit=True, name=name, description=description)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.uid} {self.name} {self.observation} {self.image}>"


class ObservationToAnnotationRelation(ItemRelation):
    """Defines a relationship between an observation and a annotation schema type."""

    observation_to_annotation_observation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("observation_schema.uid")
    )
    observation_to_annotation_annotation_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("annotation_schema.uid")
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemRelationType.OBSERVARTION_TO_ANNOTATION,
    }
    observation: Mapped["ObservationSchema"] = db.relationship(
        "ObservationSchema",
        foreign_keys=[observation_to_annotation_observation_uid],
        back_populates="annotations",
    )  # type: ignore
    annotation: Mapped["AnnotationSchema"] = db.relationship(
        "AnnotationSchema",
        foreign_keys=[observation_to_annotation_annotation_uid],
        back_populates="observations",
    )  # type: ignore

    def __init__(
        self,
        name: str,
        observation: "ObservationSchema",
        annotation: "AnnotationSchema",
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
        super().__init__(add=True, commit=True, name=name, description=description)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.uid} {self.name} {self.observation} {self.annotation}>"


class ItemSchema(DbBase):
    """A type of item that are included in a schema."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    display_name: Mapped[str] = db.Column(db.String(128))
    item_value_type: Mapped[ItemValueType] = db.Column(db.Enum(ItemValueType))
    display_order: Mapped[int] = db.Column(db.Integer())

    attributes: Mapped[List[AttributeSchema]] = db.relationship(
        AttributeSchema,
        lazy=True,
        single_parent=True,
        cascade="all, delete-orphan",
    )  # type: ignore

    schema: Mapped[Schema] = db.relationship(Schema, cascade="all, delete")  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("schema.uid"))

    __mapper_args__ = {
        "polymorphic_on": "item_value_type",
    }
    __table_args__ = (db.UniqueConstraint("schema_uid", "name"),)

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        attributes: Optional[List[AttributeSchema]] = None,
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
            add=True,
            commit=True,
            schema_uid=schema.uid,
            name=name,
            display_name=display_name,
            display_order=display_order,
        )

    @classmethod
    def get_for_schema(
        cls: Type[ItemSchemaType], schema: Union[Schema, UUID]
    ) -> Iterable[ItemSchemaType]:
        if isinstance(schema, Schema):
            schema = schema.uid
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema).order_by(cls.display_order)
        )

    @classmethod
    def get(
        cls: Type[ItemSchemaType], schema: Union[Schema, UUID], name: str
    ) -> ItemSchemaType:
        if isinstance(schema, Schema):
            schema = schema.uid
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema, name=name)
        ).one()

    @classmethod
    def get_optional(
        cls: Type[ItemSchemaType], schema: Union[Schema, UUID], name: str
    ) -> Optional[ItemSchemaType]:
        if isinstance(schema, Schema):
            schema = schema.uid
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema, name=name)
        ).one_or_none()

    @classmethod
    def get_by_uid(cls: Type[ItemSchemaType], uid: UUID) -> Optional[ItemSchemaType]:
        return db.session.get(cls, uid)


class ObservationSchema(ItemSchema):
    """A schema item type for observations."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    )

    samples: Mapped[List[ObservationToSampleRelation]] = db.relationship(
        "ObservationToSampleRelation",
        back_populates="observation",
        foreign_keys=[
            ObservationToSampleRelation.observation_to_sample_observation_uid
        ],
    )  # type: ignore
    images: Mapped[List[ObservationToImageRelation]] = db.relationship(
        ObservationToImageRelation,
        back_populates="observation",
        foreign_keys=[ObservationToImageRelation.observation_to_image_observation_uid],
    )  # type: ignore
    annotations: Mapped[List[ObservationToAnnotationRelation]] = db.relationship(
        "ObservationToAnnotationRelation",
        back_populates="observation",
        foreign_keys=[
            ObservationToAnnotationRelation.observation_to_annotation_observation_uid
        ],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.OBSERVATION,
    }

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        items: Optional[Sequence[ObservationRelationDefinition]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
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
        if items is not None:
            self.annotations = [
                ObservationToAnnotationRelation(
                    item.name, self, item.item, item.description
                )
                for item in items
                if isinstance(item.item, AnnotationSchema)
            ]
            self.images = [
                ObservationToImageRelation(item.name, self, item.item, item.description)
                for item in items
                if isinstance(item.item, ImageSchema)
            ]
            self.samples = [
                ObservationToSampleRelation(
                    item.name, self, item.item, item.description
                )
                for item in items
                if isinstance(item.item, SampleSchema)
            ]
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            display_order=display_order,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        items: Optional[Sequence[ObservationRelationDefinition]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "ObservationSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(
                schema, name, display_name, display_order, items, attributes
            )
        return item_schema


class AnnotationSchema(ItemSchema):
    """A schema item type for annotations."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    )

    images: Mapped[List[AnnotationToImageRelation]] = db.relationship(
        AnnotationToImageRelation,
        back_populates="annotation",
        foreign_keys=[AnnotationToImageRelation.annotation_to_image_annotation_uid],
    )  # type: ignore

    observations: Mapped[List[ObservationToAnnotationRelation]] = db.relationship(
        ObservationToAnnotationRelation,
        back_populates="annotation",
        foreign_keys=[
            ObservationToAnnotationRelation.observation_to_annotation_annotation_uid
        ],
    )  # type: ignore
    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.ANNOTATION,
    }

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        images: Optional[Sequence[AnnotationRelationDefinition]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
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
            AnnotationToImageRelation(image.name, self, image.image, image.description)
            for image in images or []
        ] or []  # type: ignore
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            display_order=display_order,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        images: Optional[Sequence[AnnotationRelationDefinition]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "AnnotationSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(
                schema, name, display_name, display_order, images, attributes
            )
        return item_schema


class ImageSchema(ItemSchema):
    """A schema item type for images."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    )

    samples: Mapped[List[ImageToSampleRelation]] = db.relationship(
        "ImageToSampleRelation",
        back_populates="image",
        foreign_keys=[ImageToSampleRelation.image_to_sample_image_uid],
    )  # type: ignore

    annotations: Mapped[List[AnnotationToImageRelation]] = db.relationship(
        AnnotationToImageRelation,
        back_populates="image",
        foreign_keys=[AnnotationToImageRelation.annotation_to_image_image_uid],
    )  # type: ignore
    observations: Mapped[List[ObservationToImageRelation]] = db.relationship(
        ObservationToImageRelation,
        back_populates="image",
        foreign_keys=[ObservationToImageRelation.observation_to_image_image_uid],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.IMAGE,
    }

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        samples: Optional[Sequence[ImageRelationDefinition]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
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
        self.samples = [
            ImageToSampleRelation(sample.name, self, sample.sample, sample.description)
            for sample in samples or []
        ]
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            display_order=display_order,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        samples: Optional[Sequence[ImageRelationDefinition]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "ImageSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(
                schema, name, display_name, display_order, samples, attributes
            )
        return item_schema


class SampleSchema(ItemSchema):
    """A schema item type for samples."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    )

    # Relationships
    parents: Mapped[List[SampleToSampleRelation]] = db.relationship(
        "SampleToSampleRelation",
        cascade="all, delete",
        back_populates="child",
        foreign_keys=[SampleToSampleRelation.child_uid],
    )  # type: ignore

    children: Mapped[List[SampleToSampleRelation]] = db.relationship(
        "SampleToSampleRelation",
        cascade="all, delete",
        back_populates="parent",
        foreign_keys=[SampleToSampleRelation.parent_uid],
    )  # type: ignore

    images: Mapped[List[ImageToSampleRelation]] = db.relationship(
        ImageToSampleRelation,
        back_populates="sample",
        foreign_keys=[ImageToSampleRelation.image_to_sample_sample_uid],
    )  # type: ignore

    observations: Mapped[List[ObservationToSampleRelation]] = db.relationship(
        ObservationToSampleRelation,
        back_populates="sample",
        foreign_keys=[ObservationToSampleRelation.observation_to_sample_sample_uid],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.SAMPLE,
    }

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        children: Optional[Sequence[SampleRelationDefinition]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ):
        self.children = [
            SampleToSampleRelation(
                sample.name,
                self,
                sample.child,
                sample.min_parents,
                sample.max_parents,
                sample.min_children,
                sample.max_children,
                sample.description,
            )
            for sample in children or []
        ]  # type: ignore
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            display_order=display_order,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        display_order: int,
        children: Optional[Sequence[SampleRelationDefinition]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "SampleSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(
                schema, name, display_name, display_order, children, attributes
            )
        return item_schema
