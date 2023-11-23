"""
Attribute schemas are used for attributes that have a single value. The schemas are
value type specific and can specify restrictions on the value, e.g. allowed values
or min-max range.
"""
from __future__ import annotations
from typing import (
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
)
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import NotAllowedActionError, db
from slidetap.database.schema.schema import Schema
from slidetap.model import AttributeValueType, DatetimeType

AttributeSchemaType = TypeVar("AttributeSchemaType", bound="AttributeSchema")


class AttributeSchema(db.Model):
    """Base attribute schema."""

    attribute_schema_to_attribute_schema = db.Table(
        "attribute_schema_to_attribute_schema",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("attribute_schema.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("attribute_schema.uid"),
            primary_key=True,
        ),
    )

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    tag: Mapped[str] = db.Column(db.String(128))
    name: Mapped[str] = db.Column(db.String(128))
    display_name: Mapped[str] = db.Column(db.String(128))
    attribute_value_type: Mapped[AttributeValueType] = db.Column(
        db.Enum(AttributeValueType)
    )

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("schema.uid"))
    # parent_attribute_schema_uid: Mapped[Optional[UUID]] = db.Column(
    #     Uuid, db.ForeignKey("attribute_schema.uid")
    # )
    item_schema_uid: Mapped[Optional[UUID]] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )
    # Relations
    parents: Mapped[List[AttributeSchema]] = db.relationship(
        "AttributeSchema",
        secondary=attribute_schema_to_attribute_schema,
        primaryjoin=(uid == attribute_schema_to_attribute_schema.c.child_uid),
        secondaryjoin=(uid == attribute_schema_to_attribute_schema.c.parent_uid),
        back_populates="attributes",
    )  # type: ignore
    attributes: Mapped[List[AttributeSchema]] = db.relationship(
        "AttributeSchema",
        secondary=attribute_schema_to_attribute_schema,
        primaryjoin=(uid == attribute_schema_to_attribute_schema.c.parent_uid),
        secondaryjoin=(uid == attribute_schema_to_attribute_schema.c.child_uid),
        back_populates="parents",
        # cascade="all, delete-orphan",
    )  # type: ignore

    # Relations
    schema: Mapped[Schema] = db.relationship(Schema)  # type: ignore

    __mapper_args__ = {
        "polymorphic_on": "attribute_value_type",
    }
    __table_args__ = (db.UniqueConstraint("schema_uid", "name"),)

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        attributes: Optional[Sequence[AttributeSchema]] = None,
        **kwargs,
    ):
        """Add a new schema item type to the database.

        Parameters
        ----------
        schema: 'Schema'
            The schema the item type belongs to.
        name: str
            The name of the item type.
        tag: str
            The tag of the item type
        """

        # self.schema = schema
        existing_schema = self.get_optional(schema, name)
        if existing_schema is not None:
            raise NotAllowedActionError(
                f"Not allowed to add attribute schema with same name {name} as existing schema"
            )
        if tag is None:
            tag = name
        if attributes is None:
            attributes = []
        super().__init__(
            schema_uid=schema.uid,
            name=name,
            display_name=display_name,
            tag=tag,
            attributes=attributes,
            **kwargs,
        )
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get(
        cls: Type[AttributeSchemaType], schema: Schema, name: str
    ) -> AttributeSchemaType:
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema.uid, name=name)
        ).one()

    @classmethod
    def get_optional(
        cls: Type[AttributeSchemaType], schema: Schema, name: str
    ) -> Optional[AttributeSchemaType]:
        return db.session.scalars(
            select(cls).filter_by(schema_uid=schema.uid, name=name)
        ).one_or_none()

    @classmethod
    def get_by_uid(cls: Type[AttributeSchemaType], uid: UUID) -> AttributeSchemaType:
        return db.session.scalars(select(cls).filter_by(uid=uid)).one()

    @classmethod
    def get_for_schema(cls, schema_uid: UUID) -> Sequence["AttributeSchema"]:
        return db.session.scalars(select(cls).filter_by(schema_uid=schema_uid)).all()


class StringAttributeSchema(AttributeSchema):
    """Schema for string attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
    ):
        super().__init__(schema=schema, name=name, display_name=display_name, tag=tag)

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.STRING,
    }
    __tablename__ = "string_attribute_schema"

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
    ) -> "StringAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(schema, name, display_name, tag)
        return attribute_schema


class EnumAttributeSchema(AttributeSchema):
    """Schema for enum attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    allowed_values: Mapped[List[str]] = db.Column(db.PickleType)

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        allowed_values: Optional[Sequence[str]] = None,
    ):
        if allowed_values is not None:
            allowed_values = list(allowed_values)
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            allowed_values=allowed_values,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.ENUM,
    }
    __tablename__ = "enum_attribute_schema"

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        allowed_values: Optional[Sequence[str]] = None,
    ) -> "EnumAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(schema, name, display_name, tag, allowed_values)
        return attribute_schema


class DatetimeAttributeSchema(AttributeSchema):
    """Schema for datetime attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )

    datetime_type: Mapped[DatetimeType] = db.Column(db.Enum(DatetimeType))

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.DATETIME,
    }
    __tablename__ = "datetime_attribute_schema"

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        datetime_type: DatetimeType = DatetimeType.DATETIME,
    ):
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            datetime_type=datetime_type,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        datetime_type: DatetimeType = DatetimeType.DATETIME,
    ) -> "DatetimeAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(schema, name, display_name, tag, datetime_type)
        return attribute_schema


class NumericAttributeSchema(AttributeSchema):
    """Schema for numeric attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    is_int: Mapped[bool] = db.Column(db.Boolean)
    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.NUMERIC,
    }
    __tablename__ = "numeric_attribute_schema"

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        is_int: bool = False,
    ):
        super().__init__(schema, name, display_name, tag, is_int=is_int)

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        is_int: bool = False,
    ) -> "NumericAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(schema, name, display_name, tag, is_int)
        return attribute_schema


class MeasurementAttributeSchema(AttributeSchema):
    """Schema for measurement attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    allowed_units: Mapped[List[str]] = db.Column(db.PickleType)

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.MEASUREMENT,
    }
    __tablename__ = "measurement_attribute_schema"

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        allowed_units: Optional[Sequence[str]] = None,
    ):
        if allowed_units is not None:
            allowed_units = list(allowed_units)
        super().__init__(schema, name, display_name, tag, allowed_units=allowed_units)

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        allowed_units: Optional[Sequence[str]] = None,
    ) -> "MeasurementAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(schema, name, display_name, tag, allowed_units)
        return attribute_schema


class CodeAttributeSchema(AttributeSchema):
    """Schema for code attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    allowed_schemas: Mapped[List[str]] = db.Column(db.PickleType)

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.CODE,
    }
    __tablename__ = "code_attribute_schema"

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        allowed_schemas: Optional[Sequence[str]] = None,
    ):
        if allowed_schemas is not None:
            allowed_schemas = list(allowed_schemas)
        super().__init__(
            schema, name, display_name, tag, allowed_schemas=allowed_schemas
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        allowed_schemas: Optional[Sequence[str]] = None,
    ) -> "CodeAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(schema, name, display_name, tag, allowed_schemas)
        return attribute_schema


class BooleanAttributeSchema(AttributeSchema):
    """Schema for boolean attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    true_display_value: Mapped[Optional[str]] = db.Column(db.String(128))
    false_display_value: Mapped[Optional[str]] = db.Column(db.String(128))

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        display_values: Optional[Tuple[str, str]] = None,
    ):
        if display_values is not None:
            true_display_value, false_display_value = display_values
        else:
            true_display_value, false_display_value = None, None
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            true_display_value=true_display_value,
            false_display_value=false_display_value,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.BOOLEAN,
    }
    __tablename__ = "boolean_attribute_schema"

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        display_values: Optional[Tuple[str, str]] = None,
    ) -> "BooleanAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(schema, name, display_name, tag, display_values)
        return attribute_schema


class ObjectAttributeSchema(AttributeSchema):

    """
    A schema item type for attribute objects.

    An attribute object can contain multiple attributes and also nested attribute
    objects. The scema can therefore link to other attribute and attribute object
    schemas.
    """

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    display_attributes_in_parent: Mapped[bool] = db.Column(db.Boolean)
    display_value_format_string: Mapped[Optional[str]] = db.Column(db.String(512))

    # Relations

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        attributes: Optional[List[AttributeSchema]],
        tag: Optional[str] = None,
        display_attributes_in_parent: bool = False,
        display_value_format_string: Optional[str] = None,
    ):
        """Add a new schema item type to the database.

        Parameters
        ----------
        schema: 'Schema'
            The schema the item type belongs to.
        name: str
            The name of the item type.
        attributes: Optional[List[AttributeSchema]] = None
            Attributes that the object attribute can have. If None the attribute can
            have any attribute.
        """

        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            attributes=attributes,
            display_attributes_in_parent=display_attributes_in_parent,
            display_value_format_string=display_value_format_string,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        attributes: Optional[List[AttributeSchema]],
        tag: Optional[str] = None,
        display_attributes_in_parent: bool = False,
        display_value_format_string: Optional[str] = None,
    ) -> "ObjectAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                attributes,
                tag,
                display_attributes_in_parent,
                display_value_format_string,
            )
        return attribute_schema

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.OBJECT,
    }
    __tablename__ = "object_attribute_schema"


class ListAttributeSchema(AttributeSchema):
    """
    A schema attribute type for an attribute that can contain several attributes of
    the same type.
    """

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    display_attributes_in_parent: Mapped[bool] = db.Column(db.Boolean)

    # Relations
    @property
    def attribute(self) -> AttributeSchema:
        return self.attributes[0]

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        attribute: AttributeSchema,
        tag: Optional[str] = None,
        display_attributes_in_parent: bool = False,
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

        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            attributes=[attribute],
            display_attributes_in_parent=display_attributes_in_parent,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        attribute: AttributeSchema,
        tag: Optional[str] = None,
        display_attributes_in_parent: bool = False,
    ) -> "ListAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                attribute,
                tag,
                display_attributes_in_parent,
            )
        return attribute_schema

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.LIST,
    }
    __tablename__ = "attribute_list_schema"


class UnionAttributeSchema(AttributeSchema):

    """
    A schema item type for attribute that can have different defined schemas.
    """

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    # Relations

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        attributes: List[AttributeSchema],
        tag: Optional[str] = None,
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

        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            attributes=attributes,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        attributes: List[AttributeSchema],
        tag: Optional[str] = None,
    ) -> "UnionAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                attributes,
                tag,
            )
        return attribute_schema

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.UNION,
    }
    __tablename__ = "attribute_union_schema"
