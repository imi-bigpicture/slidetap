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

"""
Attribute schemas are used for attributes that have a single value. The schemas are
value type specific and can specify restrictions on the value, e.g. allowed values
or min-max range.
"""

from __future__ import annotations

from abc import abstractmethod
from types import MappingProxyType
from typing import (
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
)
from uuid import UUID, uuid4

from sqlalchemy import JSON, Uuid, select
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import DbBase, db
from slidetap.database.types import (
    attribute_schema_db_type,
    attribute_schema_dict_db_type,
)
from slidetap.model import AttributeValueType, DatetimeType
from slidetap.model.schema.attribute_schema import (
    AttributeSchema,
    AttributeSchemaType,
    BooleanAttributeSchema,
    CodeAttributeSchema,
    DatetimeAttributeSchema,
    EnumAttributeSchema,
    ListAttributeSchema,
    MeasurementAttributeSchema,
    NumericAttributeSchema,
    ObjectAttributeSchema,
    StringAttributeSchema,
    UnionAttributeSchema,
)

DatabaseAttributeSchemaType = TypeVar(
    "DatabaseAttributeSchemaType", bound="DatabaseAttributeSchema"
)


class DatabaseAttributeSchema(DbBase, Generic[AttributeSchemaType]):
    """Base attribute schema."""

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
    # schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("root_schema.uid"))
    project_schema_uid: Mapped[Optional[UUID]] = db.Column(
        Uuid, db.ForeignKey("project_schema.uid")
    )

    item_schema_uid: Mapped[Optional[UUID]] = db.Column(
        Uuid, db.ForeignKey("item_schema.uid")
    )

    # Relations
    # schema: Mapped[DatabaseRootSchema] = db.relationship(DatabaseRootSchema)  # type: ignore

    __mapper_args__ = {
        "polymorphic_on": "attribute_value_type",
        "polymorphic_abstract": True,
    }
    __tablename__ = "attribute_schema"
    # __table_args__ = (db.UniqueConstraint("schema_uid", "name"),)

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        tag: Optional[str],
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

        super().__init__(
            uid=uid,
            name=name,
            display_name=display_name,
            tag=tag,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
            add=True,
            commit=True,
            **kwargs,
        )

    @classmethod
    def get_or_create_from_model(
        cls, model: AttributeSchema
    ) -> "DatabaseAttributeSchema":
        if isinstance(model, StringAttributeSchema):
            return DatabaseStringAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, EnumAttributeSchema):
            return DatabaseEnumAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, DatetimeAttributeSchema):
            return DatabaseDatetimeAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, NumericAttributeSchema):
            return DatabaseNumericAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, MeasurementAttributeSchema):
            return DatabaseMeasurementAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, CodeAttributeSchema):
            return DatabaseCodeAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, BooleanAttributeSchema):
            return DatabaseBooleanAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, ObjectAttributeSchema):
            return DatabaseObjectAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, ListAttributeSchema):
            return DatabaseListAttributeSchema.get_or_create_from_model(model)
        if isinstance(model, UnionAttributeSchema):
            return DatabaseUnionAttributeSchema.get_or_create_from_model(model)
        raise ValueError(f"Unsupported attribute schema type: {model}")

    # @classmethod
    # def get(
    #     cls: Type[DatabaseAttributeSchemaType], schema: DatabaseRootSchema, name: str
    # ) -> DatabaseAttributeSchemaType:
    #     return db.session.scalars(
    #         select(cls).filter_by(schema_uid=schema.uid, name=name)
    #     ).one()

    # @classmethod
    # def get_optional(
    #     cls: Type[DatabaseAttributeSchemaType], schema: DatabaseRootSchema, name: str
    # ) -> Optional[DatabaseAttributeSchemaType]:
    #     return db.session.scalars(
    #         select(cls).filter_by(schema_uid=schema.uid, name=name)
    #     ).one_or_none()

    @classmethod
    def get(
        cls: Type[DatabaseAttributeSchemaType], uid: UUID
    ) -> DatabaseAttributeSchemaType:
        schema = db.session.get(cls, uid)
        if schema is None:
            raise ValueError(f"Attribute schema with uid {uid} not found")
        return schema

    @classmethod
    def get_for_schema(cls, schema_uid: UUID) -> Iterable["DatabaseAttributeSchema"]:
        return db.session.scalars(select(cls).filter_by(schema_uid=schema_uid))

    @property
    @abstractmethod
    def model(self) -> AttributeSchemaType:
        raise NotImplementedError()


class DatabaseStringAttributeSchema(DatabaseAttributeSchema):
    """Schema for string attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        tag: Optional[str],
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        super().__init__(
            uid=uid,
            name=name,
            display_name=display_name,
            tag=tag,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.STRING,
    }
    __tablename__ = "string_attribute_schema"

    @classmethod
    def get_or_create_from_model(
        cls, model: StringAttributeSchema
    ) -> DatabaseStringAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            tag=model.tag,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    @property
    def model(self) -> StringAttributeSchema:
        return StringAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseEnumAttributeSchema(DatabaseAttributeSchema):
    """Schema for enum attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    allowed_values: Mapped[List[str]] = mapped_column(JSON)

    def __init__(
        self,
        uid: UUID,
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
            uid=uid,
            name=name,
            display_name=display_name,
            tag=tag,
            allowed_values=allowed_values,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.ENUM,
    }
    __tablename__ = "enum_attribute_schema"

    @classmethod
    def get_or_create_from_model(
        cls, model: EnumAttributeSchema
    ) -> DatabaseEnumAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            tag=model.tag,
            allowed_values=model.allowed_values,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    @property
    def model(self) -> EnumAttributeSchema:
        return EnumAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            allowed_values=tuple(self.allowed_values),
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseDatetimeAttributeSchema(DatabaseAttributeSchema):
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
        uid: UUID,
        name: str,
        display_name: str,
        tag: Optional[str],
        datetime_type: DatetimeType,
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        super().__init__(
            uid=uid,
            name=name,
            display_name=display_name,
            tag=tag,
            datetime_type=datetime_type,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )

    @classmethod
    def get_or_create_from_model(
        cls, model: DatetimeAttributeSchema
    ) -> DatabaseDatetimeAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            tag=model.tag,
            datetime_type=model.datetime_type,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    @property
    def model(self) -> DatetimeAttributeSchema:
        return DatetimeAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            datetime_type=self.datetime_type,
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseNumericAttributeSchema(DatabaseAttributeSchema):
    """Schema for numeric attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    is_integer: Mapped[bool] = db.Column(db.Boolean)
    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.NUMERIC,
    }
    __tablename__ = "numeric_attribute_schema"

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        tag: Optional[str],
        is_integer: bool,
        display_in_table: bool,
        optional: bool,
        read_only: bool,
    ):
        super().__init__(
            uid,
            name,
            display_name,
            tag,
            is_integer=is_integer,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )

    @classmethod
    def get_or_create_from_model(
        cls, model: NumericAttributeSchema
    ) -> DatabaseNumericAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            tag=model.tag,
            is_integer=model.is_integer,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    @property
    def model(self) -> NumericAttributeSchema:
        return NumericAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            is_integer=self.is_integer,
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseMeasurementAttributeSchema(DatabaseAttributeSchema):
    """Schema for measurement attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    allowed_units: Mapped[List[str]] = mapped_column(JSON)

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.MEASUREMENT,
    }
    __tablename__ = "measurement_attribute_schema"

    def __init__(
        self,
        uid: UUID,
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
            uid,
            name,
            display_name,
            tag,
            allowed_units=allowed_units,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )

    @classmethod
    def get_or_create_from_model(
        cls, model: MeasurementAttributeSchema
    ) -> DatabaseMeasurementAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            tag=model.tag,
            allowed_units=model.allowed_units,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    @property
    def model(self) -> MeasurementAttributeSchema:
        return MeasurementAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            allowed_units=tuple(self.allowed_units),
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseCodeAttributeSchema(DatabaseAttributeSchema):
    """Schema for code attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    allowed_schemas: Mapped[Optional[List[str]]] = mapped_column(JSON)

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.CODE,
    }
    __tablename__ = "code_attribute_schema"

    def __init__(
        self,
        uid: UUID,
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
            uid,
            name,
            display_name,
            tag,
            allowed_schemas=allowed_schemas,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )

    @classmethod
    def get_or_create_from_model(
        cls, model: CodeAttributeSchema
    ) -> DatabaseCodeAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            tag=model.tag,
            allowed_schemas=model.allowed_schemas,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    @property
    def model(self) -> CodeAttributeSchema:
        return CodeAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            allowed_schemas=(
                tuple(self.allowed_schemas) if self.allowed_schemas else None
            ),
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseBooleanAttributeSchema(DatabaseAttributeSchema):
    """Schema for boolean attributes."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    true_display_value: Mapped[str] = db.Column(db.String(128))
    false_display_value: Mapped[str] = db.Column(db.String(128))

    def __init__(
        self,
        uid: UUID,
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
            uid=uid,
            name=name,
            display_name=display_name,
            tag=tag,
            true_display_value=true_display_value,
            false_display_value=false_display_value,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.BOOLEAN,
    }
    __tablename__ = "boolean_attribute_schema"

    @classmethod
    def get_or_create_from_model(
        cls, model: BooleanAttributeSchema
    ) -> DatabaseBooleanAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            tag=model.tag,
            display_values=(model.true_display_value, model.false_display_value),
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    @property
    def model(self) -> BooleanAttributeSchema:
        return BooleanAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            true_display_value=self.true_display_value,
            false_display_value=self.false_display_value,
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseObjectAttributeSchema(DatabaseAttributeSchema):
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
    attributes: Mapped[Dict[str, AttributeSchema]] = mapped_column(
        attribute_schema_dict_db_type
    )

    # Relations

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        attributes: Dict[str, AttributeSchema],
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
            uid=uid,
            name=name,
            display_name=display_name,
            tag=tag,
            display_attributes_in_parent=display_attributes_in_parent,
            display_value_format_string=display_value_format_string,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )
        self.attributes = attributes or {}

    @classmethod
    def get_or_create_from_model(
        cls, model: ObjectAttributeSchema
    ) -> DatabaseObjectAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            attributes=dict(model.attributes),
            tag=model.tag,
            display_attributes_in_parent=model.display_attributes_in_parent,
            display_value_format_string=model.display_value_format_string,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.OBJECT,
    }
    __tablename__ = "object_attribute_schema"

    def extend(self, tag: str, attribute: AttributeSchema) -> None:
        if tag not in self.attributes:
            self.attributes[tag] = attribute

    @property
    def model(self) -> ObjectAttributeSchema:
        return ObjectAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            display_attributes_in_parent=self.display_attributes_in_parent,
            display_value_format_string=self.display_value_format_string,
            attributes=MappingProxyType(self.attributes),
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseListAttributeSchema(DatabaseAttributeSchema):
    """
    A schema attribute type for an attribute that can contain several attributes of
    the same type.
    """

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    display_attributes_in_parent: Mapped[bool] = db.Column(db.Boolean)
    attribute: Mapped[AttributeSchema] = mapped_column(attribute_schema_db_type)

    def __init__(
        self,
        uid: UUID,
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
            uid=uid,
            name=name,
            display_name=display_name,
            tag=tag,
            display_attributes_in_parent=display_attributes_in_parent,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )
        self.attribute = attribute

    @classmethod
    def get_or_create_from_model(
        cls, model: ListAttributeSchema
    ) -> DatabaseListAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            attribute=model.attribute,
            tag=model.tag,
            display_attributes_in_parent=model.display_attributes_in_parent,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.LIST,
    }
    __tablename__ = "attribute_list_schema"

    @property
    def model(self) -> ListAttributeSchema:
        return ListAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            attribute=self.attribute,
            display_attributes_in_parent=self.display_attributes_in_parent,
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )


class DatabaseUnionAttributeSchema(DatabaseAttributeSchema):
    """
    A schema item type for attribute that can have different defined schemas.
    """

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("attribute_schema.uid"), primary_key=True
    )
    attributes: Mapped[Dict[UUID, AttributeSchema]] = db.Column(
        attribute_schema_dict_db_type
    )
    # Relations

    def __init__(
        self,
        uid: UUID,
        name: str,
        display_name: str,
        attributes: Dict[UUID, AttributeSchema],
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
            uid=uid,
            name=name,
            display_name=display_name,
            tag=tag,
            display_in_table=display_in_table,
            optional=optional,
            read_only=read_only,
        )
        self.attributes = attributes

    @classmethod
    def get_or_create_from_model(
        cls, model: UnionAttributeSchema
    ) -> DatabaseUnionAttributeSchema:
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        return cls(
            uid=model.uid,
            name=model.name,
            display_name=model.display_name,
            attributes=dict(model.attributes),
            tag=model.tag,
            display_in_table=model.display_in_table,
            optional=model.optional,
            read_only=model.read_only,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.UNION,
    }
    __tablename__ = "attribute_union_schema"

    def extend(self, attribute: AttributeSchema) -> None:
        if attribute.uid not in self.attributes:
            self.attributes[attribute.uid] = attribute

    @property
    def model(self) -> UnionAttributeSchema:
        return UnionAttributeSchema(
            uid=self.uid,
            tag=self.tag,
            name=self.name,
            display_name=self.display_name,
            attributes=MappingProxyType(self.attributes),
            optional=self.optional,
            read_only=self.read_only,
            display_in_table=self.display_in_table,
        )
