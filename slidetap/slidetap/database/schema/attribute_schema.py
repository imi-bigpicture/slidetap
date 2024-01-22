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

from slidetap.database.db import DbBase, db
from slidetap.database.schema.schema import Schema
from slidetap.model import AttributeValueType, DatetimeType

AttributeSchemaType = TypeVar("AttributeSchemaType", bound="AttributeSchema")


class AttributeSchema(DbBase):
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
    display_in_table: Mapped[bool] = db.Column(db.Boolean, default=True)
    optional: Mapped[bool] = db.Column(db.Boolean, default=False)
    read_only: Mapped[bool] = db.Column(db.Boolean, default=False)

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
        lazy="noload",
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
        "polymorphic_abstract": True,
    }
    __table_args__ = (db.UniqueConstraint("schema_uid", "name"),)

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str],
        attributes: Optional[Sequence[AttributeSchema]],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
        **kwargs,
    ):
        """Add a new attribute schema to the database.

        Parameters
        ----------
        schema: Schema
            The schema the attribute schema belongs to.
        name: str
            The name of the schema.
        display_name: str
            The display name of the schema.
        tag: Optional[str]
            The tag of the schema. If None the name is used as tag.
        attributes: Optional[Sequence[AttributeSchema]]
            Attributes that the schema can have.
        display_in_table: bool
            If the attribute should be displayed in table.
        optional: bool
            If the attribute is required.
        read_only: bool
            If the attribute is read only (not allowed to be changed).
        """

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
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            add=True,
            commit=True,
            **kwargs,
        )

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
        schema = db.session.get(cls, uid)
        if schema is None:
            raise ValueError(f"Attribute schema with uid {uid} not found")
        return schema

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
        tag: Optional[str],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            attributes=None,
        )

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
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
    ) -> "StringAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                tag,
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
            )
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
        tag: Optional[str],
        allowed_values: Optional[Sequence[str]],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        if allowed_values is not None:
            allowed_values = list(allowed_values)
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            allowed_values=allowed_values,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            attributes=None,
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
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
    ) -> "EnumAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                tag,
                allowed_values,
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
            )
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
        tag: Optional[str],
        datetime_type: DatetimeType,
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            datetime_type=datetime_type,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            attributes=None,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        datetime_type: DatetimeType = DatetimeType.DATETIME,
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
    ) -> "DatetimeAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                tag,
                datetime_type,
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
            )
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
        tag: Optional[str],
        is_int: bool,
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        super().__init__(
            schema,
            name,
            display_name,
            tag,
            is_int=is_int,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            attributes=None,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        is_int: bool = False,
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
    ) -> "NumericAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                tag,
                is_int,
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
            )
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
        tag: Optional[str],
        allowed_units: Optional[Sequence[str]],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        if allowed_units is not None:
            allowed_units = list(allowed_units)
        super().__init__(
            schema,
            name,
            display_name,
            tag,
            allowed_units=allowed_units,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            attributes=None,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        allowed_units: Optional[Sequence[str]] = None,
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
    ) -> "MeasurementAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                tag,
                allowed_units,
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
            )
        return attribute_schema


class CodeAttributeSchema(AttributeSchema):
    """Schema for code attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    allowed_schemas: Mapped[Optional[List[str]]] = db.Column(db.PickleType)

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.CODE,
    }
    __tablename__ = "code_attribute_schema"

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str],
        allowed_schemas: Optional[Sequence[str]],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        if allowed_schemas is not None:
            allowed_schemas = list(allowed_schemas)
        super().__init__(
            schema,
            name,
            display_name,
            tag,
            allowed_schemas=allowed_schemas,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            attributes=None,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str] = None,
        allowed_schemas: Optional[Sequence[str]] = None,
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
    ) -> "CodeAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                tag,
                allowed_schemas,
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
            )
        return attribute_schema


class BooleanAttributeSchema(AttributeSchema):
    """Schema for boolean attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    true_display_value: Mapped[str] = db.Column(db.String(128))
    false_display_value: Mapped[str] = db.Column(db.String(128))

    def __init__(
        self,
        schema: Schema,
        name: str,
        display_name: str,
        tag: Optional[str],
        display_values: Optional[Tuple[str, str]],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        if display_values is not None:
            true_display_value, false_display_value = display_values
        else:
            true_display_value, false_display_value = "Yes", "No"
        super().__init__(
            schema=schema,
            name=name,
            display_name=display_name,
            tag=tag,
            true_display_value=true_display_value,
            false_display_value=false_display_value,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            attributes=None,
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
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
    ) -> "BooleanAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                tag,
                display_values,
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
            )
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
        tag: Optional[str],
        display_attributes_in_parent: bool,
        display_value_format_string: Optional[str],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
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
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
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
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
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
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
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
        tag: Optional[str],
        display_attributes_in_parent: bool,
        display_in_table: bool,
        optional: bool,
        read_only: bool,
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
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
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
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
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
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
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
        tag: Optional[str],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
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
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )

    @classmethod
    def get_or_create(
        cls,
        schema: Schema,
        name: str,
        display_name: str,
        attributes: List[AttributeSchema],
        tag: Optional[str] = None,
        display_in_table: bool = True,
        optional: bool = False,
        read_only: bool = False,
    ) -> "UnionAttributeSchema":
        attribute_schema = cls.get_optional(schema, name)
        if attribute_schema is None:
            attribute_schema = cls(
                schema,
                name,
                display_name,
                attributes,
                tag,
                display_in_table=display_in_table,
                optional=optional,
                read_only=read_only,
            )
        return attribute_schema

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.UNION,
    }
    __tablename__ = "attribute_union_schema"
