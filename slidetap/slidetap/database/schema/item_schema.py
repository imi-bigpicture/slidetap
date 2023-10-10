"""Item schemas define Items (e.g. Sample) with attributes and parents"""
from typing import List, Optional, Sequence, Type, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped

from slidetap.database.db import db
from slidetap.database.schema.attribute_schema import AttributeSchema
from slidetap.database.schema.schema import Schema
from slidetap.model import ItemValueType

ItemSchemaType = TypeVar("ItemSchemaType", bound="ItemSchema")


class ItemSchema(db.Model):
    """A type of item that are included in a schema."""

    # Table for mapping many-to-many schema item type to schema item type.
    item_schema_to_item_schema = db.Table(
        "item_schema_to_item_schema",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("item_schema.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("item_schema.uid"),
            primary_key=True,
        ),
    )

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    display_name: Mapped[str] = db.Column(db.String(128))
    item_value_type: Mapped[ItemValueType] = db.Column(db.Enum(ItemValueType))

    # Relationships
    parents: Mapped[List["ItemSchema"]] = db.relationship(
        "ItemSchema",
        secondary=item_schema_to_item_schema,
        lazy=True,
        primaryjoin=(uid == item_schema_to_item_schema.c.child_uid),
        secondaryjoin=(uid == item_schema_to_item_schema.c.parent_uid),
        cascade="all, delete",
        back_populates="children",
    )  # type: ignore

    children: Mapped[List["ItemSchema"]] = db.relationship(
        "ItemSchema",
        secondary=item_schema_to_item_schema,
        lazy=True,
        primaryjoin=(uid == item_schema_to_item_schema.c.parent_uid),
        secondaryjoin=(uid == item_schema_to_item_schema.c.child_uid),
        cascade="all, delete",
        back_populates="parents",
    )  # type: ignore

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
        parents: Optional[Sequence["ItemSchema"]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ):
        """Add a new schema item type to the database.

        Parameters
        ----------
        schema: 'Schema'
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[Dict[str, Sequence[type]]] = None
            Attributes that the item type can have.
        """
        if attributes is not None:
            self.attributes = attributes
        if parents is None:
            parents = []

        super().__init__(
            schema_uid=schema.uid,
            name=name,
            display_name=display_name,
            parents=parents,
        )
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_for_schema(cls, schema: Schema) -> Sequence["ItemSchema"]:
        return db.session.scalars(select(cls).filter_by(schema_uid=schema.uid)).all()

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
        return db.session.scalars(select(cls).filter_by(uid=uid)).one_or_none()


class SampleSchema(ItemSchema):
    """A schema item type for samples."""

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.SAMPLE,
    }

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        parents: Optional[Sequence["SampleSchema"]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ):
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            parents=parents,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        parents: Optional[Sequence["SampleSchema"]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "SampleSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(schema, name, display_name, parents, attributes)
        return item_schema


class ImageSchema(ItemSchema):
    """A schema item type for images."""

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.IMAGE,
    }

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        samples: Optional[Sequence[SampleSchema]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ):
        """Add a new image schema item type to the database.

        Parameters
        ----------
        schema: 'Schema'
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[Sequence[str]] = None
            Attributes that the item type can have.
        """
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            parents=samples,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        samples: Optional[Sequence[SampleSchema]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "ImageSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(schema, name, display_name, samples, attributes)
        return item_schema


class AnnotationSchema(ItemSchema):
    """A schema item type for annotations."""

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.ANNOTATION,
    }

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        images: Optional[Sequence[ImageSchema]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ):
        """Add a new annotation schema item type to the database.

        Parameters
        ----------
        schema: 'Schema'
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[Sequence[str]] = None
            Attributes that the item type can have.
        """
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            parents=images,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        images: Optional[Sequence[ImageSchema]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "AnnotationSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(schema, name, display_name, images, attributes)
        return item_schema


class ObservationSchema(ItemSchema):
    """A schema item type for observations."""

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.OBSERVATION,
    }

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        items: Optional[Sequence[ItemSchema]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ):
        """Add a new observation schema item type to the database.

        Parameters
        ----------
        schema: 'Schema'
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[Sequence[str]] = None,
            Attributes that the item type can have.
        """
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            parents=items,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        items: Optional[Sequence[ItemSchema]] = None,
        attributes: Optional[List[AttributeSchema]] = None,
    ) -> "ObservationSchema":
        item_schema = cls.get_optional(schema, name)
        if item_schema is None:
            item_schema = cls(schema, name, display_name, items, attributes)
        return item_schema
