"""Item schemas define Items (e.g. Sample) with attributes and parents"""
from typing import List, Optional, Sequence, Type, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import DbBase, db
from slidetap.database.schema.attribute_schema import AttributeSchema
from slidetap.database.schema.schema import Schema
from slidetap.model import ItemValueType

ItemSchemaType = TypeVar("ItemSchemaType", bound="ItemSchema")


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
        cls: Type[ItemSchemaType], schema_uid: UUID
    ) -> Sequence[ItemSchemaType]:
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema_uid).order_by(cls.display_order)
        ).all()

    @classmethod
    def get(cls: Type[ItemSchemaType], schema: Schema, name: str) -> ItemSchemaType:
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema.uid, name=name)
        ).one()

    @classmethod
    def get_optional(
        cls: Type[ItemSchemaType], schema: Schema, name: str
    ) -> Optional[ItemSchemaType]:
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema.uid, name=name)
        ).one_or_none()

    @classmethod
    def get_by_uid(cls: Type[ItemSchemaType], uid: UUID) -> Optional[ItemSchemaType]:
        return db.session.get(cls, uid)


class ObservationSchema(ItemSchema):
    """A schema item type for observations."""

    # Table for mapping many-to-many samples to observations
    sample_schema_to_observation_schema = db.Table(
        "sample_schema_to_observation_schema",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("sample_schema.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("observation_schema.uid"),
            primary_key=True,
        ),
    )
    # Table for mapping many-to-many images to observations
    image_schema_to_observation_schema = db.Table(
        "image_schema_to_observation_schema",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("image_schema.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("observation_schema.uid"),
            primary_key=True,
        ),
    )
    # Table for mapping many-to-many annotations to observations
    annotation_schema_to_observation_schema = db.Table(
        "annotation_schema_to_observation_schema",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("annotation_schema.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("observation_schema.uid"),
            primary_key=True,
        ),
    )

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    )

    samples: Mapped[List["SampleSchema"]] = db.relationship(
        "SampleSchema",
        secondary=sample_schema_to_observation_schema,
        back_populates="observations",
    )  # type: ignore
    images: Mapped[List["ImageSchema"]] = db.relationship(
        "ImageSchema",
        secondary=image_schema_to_observation_schema,
        back_populates="observations",
    )  # type: ignore
    annotations: Mapped[List["AnnotationSchema"]] = db.relationship(
        "AnnotationSchema",
        secondary=annotation_schema_to_observation_schema,
        back_populates="observations",
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
        items: Optional[Sequence[ItemSchema]] = None,
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
                item for item in items if isinstance(item, AnnotationSchema)
            ]
            self.images = [item for item in items if isinstance(item, ImageSchema)]
            self.samples = [item for item in items if isinstance(item, SampleSchema)]
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
        items: Optional[Sequence[ItemSchema]] = None,
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

    # Table for mapping many-to-many images to annotations
    image_schema_to_annotation_schema = db.Table(
        "image_schema_to_annotation_schema",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("image_schema.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("annotation_schema.uid"),
            primary_key=True,
        ),
    )

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    )

    images: Mapped[List["ImageSchema"]] = db.relationship(
        "ImageSchema",
        secondary=image_schema_to_annotation_schema,
        back_populates="annotations",
    )  # type: ignore

    observations: Mapped[List[ObservationSchema]] = db.relationship(
        ObservationSchema,
        secondary=ObservationSchema.annotation_schema_to_observation_schema,
        back_populates="annotations",
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
        images: Optional[Sequence["ImageSchema"]] = None,
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
        self.images = images or []  # type: ignore
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
        images: Optional[Sequence["ImageSchema"]] = None,
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

    # Table for mapping many-to-many samples to images
    sample_schema_to_image_schema = db.Table(
        "sample_schema_to_image_schema",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("sample_schema.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("image_schema.uid"),
            primary_key=True,
        ),
    )

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    )

    samples: Mapped[List["SampleSchema"]] = db.relationship(
        "SampleSchema", secondary=sample_schema_to_image_schema, back_populates="images"
    )  # type: ignore

    annotations: Mapped[List[AnnotationSchema]] = db.relationship(
        AnnotationSchema,
        secondary=AnnotationSchema.image_schema_to_annotation_schema,
        back_populates="images",
    )  # type: ignore
    observations: Mapped[List[ObservationSchema]] = db.relationship(
        ObservationSchema,
        secondary=ObservationSchema.image_schema_to_observation_schema,
        back_populates="images",
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
        samples: Optional[Sequence["SampleSchema"]] = None,
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
        self.samples = samples or []  # type: ignore
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
        samples: Optional[Sequence["SampleSchema"]] = None,
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

    # Table for mapping many-to-many sample item type to sample item type.
    sample_schema_to_sample_schema = db.Table(
        "sample_schema_to_sample_schema",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("sample_schema.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("sample_schema.uid"),
            primary_key=True,
        ),
    )
    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item_schema.uid", ondelete="CASCADE"), primary_key=True
    )

    # Relationships
    parents: Mapped[List["SampleSchema"]] = db.relationship(
        "SampleSchema",
        secondary=sample_schema_to_sample_schema,
        lazy=True,
        primaryjoin=(uid == sample_schema_to_sample_schema.c.child_uid),
        secondaryjoin=(uid == sample_schema_to_sample_schema.c.parent_uid),
        cascade="all, delete",
        back_populates="children",
    )  # type: ignore

    children: Mapped[List["SampleSchema"]] = db.relationship(
        "SampleSchema",
        secondary=sample_schema_to_sample_schema,
        lazy=True,
        primaryjoin=(uid == sample_schema_to_sample_schema.c.parent_uid),
        secondaryjoin=(uid == sample_schema_to_sample_schema.c.child_uid),
        cascade="all, delete",
        back_populates="parents",
    )  # type: ignore

    images: Mapped[List[ImageSchema]] = db.relationship(
        ImageSchema,
        secondary=ImageSchema.sample_schema_to_image_schema,
        back_populates="samples",
    )  # type: ignore

    observations: Mapped[List[ObservationSchema]] = db.relationship(
        ObservationSchema,
        secondary=ObservationSchema.sample_schema_to_observation_schema,
        back_populates="samples",
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
        children: Optional[Sequence["SampleSchema"]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ):
        self.children = children or []  # type: ignore
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
        children: Optional[Sequence["SampleSchema"]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "SampleSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(
                schema, name, display_name, display_order, children, attributes
            )
        return item_schema
