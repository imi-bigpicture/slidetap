"""Attributes of different value and schema types."""
from __future__ import annotations

import re
from abc import abstractmethod
from datetime import datetime
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import Uuid, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.collections import attribute_mapped_collection

from slidetap.database.db import DbBase, NotAllowedActionError, db
from slidetap.database.schema import (
    AttributeSchema,
    AttributeSchemaType,
    AttributeValueType,
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
from slidetap.model import Code, ValueStatus
from slidetap.model.measurement import Measurement

ValueType = TypeVar("ValueType")
AttributeType = TypeVar("AttributeType", bound="Attribute")


class Attribute(DbBase, Generic[AttributeSchemaType, ValueType]):
    """An attribute defined by a tag and a value"""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    mappable_value: Mapped[Optional[str]] = db.Column(db.String(512))
    valid: Mapped[bool] = db.Column(db.Boolean)
    display_value: Mapped[Optional[str]] = db.Column(db.String(512))
    attribute_value_type: Mapped[AttributeValueType] = db.Column(
        db.Enum(AttributeValueType)
    )

    # For relations
    schema_uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute_schema.uid"))
    item_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("item.uid"))
    project_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("project.uid"))
    parent_attribute_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("attribute.uid")
    )
    parent_updated_attribute_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("attribute.uid")
    )
    mapping_item_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("mapping_item.uid", use_alter=True)
    )

    # Relations
    schema: Mapped[AttributeSchemaType] = db.relationship(AttributeSchema)  # type: ignore
    # Mapping that has mapped this attribute, if mapped.
    mapping: Mapped[Optional[MappingItem]] = db.relationship(
        "MappingItem",
        back_populates="mapped_attributes",
        foreign_keys=[mapping_item_uid],
    )  # type: ignore
    # Mappings that use this attribute for mapping, if any.
    parent_mappings: Mapped[List[MappingItem]] = db.relationship(
        "MappingItem",
        back_populates="attribute",
        foreign_keys="MappingItem.attribute_uid",
    )  # type: ignore

    def __init__(
        self,
        schema: AttributeSchema,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
        **kwargs,
    ):
        """Create a new attribute.

        Parameters
        ----------
        schema: AttributeSchema
            The schema of the attribute.
        mappable_value: Optional[str] = None
            The mappable value, by default None.
        commit: bool = True
            Whether to commit the attribute to the database, by default False.
        """
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            uid=uid or uuid4(),
            add=add,
            commit=False,
            **kwargs,
        )
        self.display_value = self._set_display_value()
        self.validate()
        if commit:
            db.session.commit()

    __mapper_args__ = {
        "polymorphic_on": "attribute_value_type",
    }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.uid} {self.tag}={self.value}>"

    @hybrid_property
    def value(self) -> Optional[ValueType]:
        if self.updated_value is not None:
            return self.updated_value
        if self.mapping is not None:
            return self.mapping.attribute.value
        if self.original_value is not None:
            return self.original_value
        return None

    @hybrid_property
    @abstractmethod
    def original_value(self) -> Optional[ValueType]:
        """The original value set for the attribute."""
        raise NotImplementedError()

    @hybrid_property
    @abstractmethod
    def updated_value(self) -> Optional[ValueType]:
        """The updated value set for the attribute."""
        raise NotImplementedError()

    @abstractmethod
    def _set_display_value(self) -> Optional[str]:
        """Display value of the attribute."""
        raise NotImplementedError()

    def validate(self, update_parents: bool = True) -> bool:
        previous_valid = self.valid
        self.valid = self._validate()
        if (
            previous_valid != self.valid
            and self.parent_attribute_uid is not None
            and update_parents
        ):
            parent = db.session.get(Attribute, self.parent_attribute_uid)
            if parent is not None:
                parent.validate()
        return self.valid

    @abstractmethod
    def _validate(self) -> bool:
        """Return true if the attribute value is valid with respect to the schema."""
        raise NotImplementedError()

    @hybrid_property
    def mapping_status(self) -> ValueStatus:
        """The mapping status of the attribute."""
        if self.updated_value is not None:
            return ValueStatus.UPDATED_VALUE
        if self.original_value is not None:
            return ValueStatus.ORIGINAL_VALUE
        if self.mappable_value is None:
            return ValueStatus.NO_MAPPABLE_VALUE
        if self.mapping_item_uid is not None:
            return ValueStatus.MAPPED
        return ValueStatus.NOT_MAPPED

    @hybrid_property
    def tag(self) -> str:
        """The tag of the attribute."""
        return self.schema.tag

    @hybrid_property
    def schema_display_name(self) -> str:
        """The display name of the attribute."""
        return self.schema.display_name

    @classmethod
    def get(cls: Type[AttributeType], uid: UUID) -> Optional[AttributeType]:
        """Get attribute by uid.

        Parameters
        ----------
        uid: UUID
            The uid of the attribute.

        Returns
        -------
        Optional[AttributeType]
            The attribute or None if not found."""
        return db.session.get(cls, uid)

    def set_mapping(self, mapping: MappingItem, commit: bool = True) -> None:
        """Set the mapping of the attribute.

        Parameters
        ----------
        mapping: MappingItem
            The mapping to set.
        """
        if self.schema.read_only:
            raise NotAllowedActionError(
                f"Cannot set mapping of read only attribute {self.schema.tag}."
            )
        self.mapping = mapping
        self.display_value = self._set_display_value()
        self.validate()
        if commit:
            db.session.commit()

    def clear_mapping(self, commit: bool = True):
        """Clear the mapping of the attribute."""
        self.mapping = None
        if commit:
            db.session.commit()

    def set_value(self, value: Optional[ValueType], commit: bool = True) -> None:
        """Set the value of the attribute.

        Parameters
        ----------
        value: Optional[ValueType]
            The value to set.
        """
        if self.schema.read_only and value != self.value:
            raise NotAllowedActionError(
                f"Cannot set value of read only attribute {self.schema.tag}."
            )
        self._set_value(value)
        self.display_value = self._set_display_value()
        self.valid = self.validate()
        if commit:
            db.session.commit()

    @abstractmethod
    def _set_value(self, value: Optional[ValueType]) -> None:
        """Set the value of the attribute.

        Parameters
        ----------
        value: Optional[ValueType]
            The value to set.
        """
        raise NotImplementedError()

    def set_mappable_value(self, value: Optional[str]) -> None:
        """Set the mappable value of the attribute.

        Parameters
        ----------
        value: Optional[str]
            The mappable value to set.
        """
        self.mappable_value = value

    def recursive_get_all_attributes(self, schema_uid: UUID) -> Set["Attribute"]:
        if self.schema_uid == schema_uid:
            return set([self])
        return set()

    @classmethod
    def get_for_attribute_schema(
        cls, attribute_schema_uid: UUID
    ) -> Sequence["Attribute"]:
        return db.session.scalars(
            select(cls).filter_by(schema_uid=attribute_schema_uid)
        ).all()

    @abstractmethod
    def copy(self) -> Attribute:
        """Copy the attribute."""
        raise NotImplementedError()


class StringAttribute(Attribute[StringAttributeSchema, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[str] = db.Column(db.String(128))
    updated_value: Optional[str] = db.Column(db.String(128))

    def __init__(
        self,
        schema: StringAttributeSchema,
        value: Optional[str] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new string attribute.

        Parameters
        ----------
        schema: StringAttributeSchema
            The schema of the attribute.
        value: Optional[str] = None
            The value of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.STRING,
    }
    __tablename__ = "string_attribute"

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return self.value
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if self.value is not None and self.value != "":
            return True
        return self.schema.optional

    def _set_value(self, value: str) -> None:
        self.updated_value = value

    def copy(self) -> StringAttribute:
        return StringAttribute(
            schema=self.schema,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class EnumAttribute(Attribute[EnumAttributeSchema, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[str] = db.Column(db.String(128))
    updated_value: Optional[str] = db.Column(db.String(128))

    def __init__(
        self,
        schema: EnumAttributeSchema,
        value: Optional[str] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new enum attribute.

        Parameters
        ----------
        schema: EnumAttributeSchema
            The schema of the attribute.
        value: Optional[str] = None
            The value of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        if (
            schema.allowed_values is not None
            and value is not None
            and value not in schema.allowed_values
        ):
            raise ValueError(
                f"Value {value} for tag {schema.tag} is not in allowed vales "
                f"{schema.allowed_values}"
            )

        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.ENUM,
    }
    __tablename__ = "enum_attribute"

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return self.value
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if self.value not in self.schema.allowed_values:
            return False
        if self.value is not None and self.value != "":
            return True
        return self.schema.optional

    def _set_value(self, value: str) -> None:
        self.updated_value = value

    def copy(self) -> EnumAttribute:
        return EnumAttribute(
            schema=self.schema,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatetimeAttribute(Attribute[DatetimeAttributeSchema, datetime]):
    """An attribute defined by a tag and a datetime value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[datetime] = db.Column(db.DateTime)
    updated_value: Optional[datetime] = db.Column(db.DateTime)

    def __init__(
        self,
        schema: DatetimeAttributeSchema,
        value: Optional[datetime] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new datetime attribute.

        Parameters
        ----------
        schema: DatetimeAttributeSchema
            The schema of the attribute.
        value: Optional[datetime] = None
            The value of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.DATETIME,
    }
    __tablename__ = "datetime_attribute"

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if self.value is not None:
            return True
        return self.schema.optional

    def _set_value(self, value: datetime) -> None:
        self.updated_value = value

    def copy(self) -> DatetimeAttribute:
        return DatetimeAttribute(
            schema=self.schema,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class NumericAttribute(Attribute[NumericAttributeSchema, Union[int, float]]):
    """An attribute defined by a tag and a float value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[float] = db.Column(db.Float)
    updated_value: Optional[float] = db.Column(db.Float)

    def __init__(
        self,
        schema: NumericAttributeSchema,
        value: Optional[float] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new numeric attribute.

        Parameters
        ----------
        schema: NumericAttributeSchema
            The schema of the attribute.
        value: Optional[float] = None
            The value of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.NUMERIC,
    }
    __tablename__ = "number_attribute"

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if self.value is not None:
            return True
        return self.schema.optional

    def _set_value(self, value: float) -> None:
        self.updated_value = value

    def copy(self) -> NumericAttribute:
        return NumericAttribute(
            schema=self.schema,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class MeasurementAttribute(Attribute[MeasurementAttributeSchema, Measurement]):
    """An attribute defined by a tag and a measurement value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Measurement]] = db.Column(db.PickleType)
    updated_value: Mapped[Optional[Measurement]] = db.Column(db.PickleType)

    def __init__(
        self,
        schema: MeasurementAttributeSchema,
        value: Optional[Measurement] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new measurement attribute.

        Parameters
        ----------
        schema: MeasurementAttributeSchema
            The schema of the attribute.
        value: Optional[Measurement] = None
            The value of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.MEASUREMENT,
    }
    __tablename__ = "measurement_attribute"

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return f"{self.value.value} {self.value.unit}"
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if (
            self.value is not None
            and self.schema.allowed_units is not None
            and self.value.unit not in self.schema.allowed_units
        ):
            return False
        if self.value is not None:
            return True
        return self.schema.optional

    def _set_value(self, value: Measurement) -> None:
        self.updated_value = value

    def copy(self) -> MeasurementAttribute:
        return MeasurementAttribute(
            schema=self.schema,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class CodeAttribute(Attribute[CodeAttributeSchema, Code]):
    """An attribute defined by a tag and a code value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Code]] = db.Column(db.PickleType)
    updated_value: Mapped[Optional[Code]] = db.Column(db.PickleType)

    def __init__(
        self,
        schema: CodeAttributeSchema,
        value: Optional[Code] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new code attribute.

        Parameters
        ----------
        schema: CodeAttributeSchema
            The schema of the attribute.
        value: Optional[Code] = None
            The value of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.CODE,
    }
    __tablename__ = "code_attribute"

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None and self.value.meaning is not None:
            return str(self.value.meaning)
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if self.value is not None:
            if (
                self.value.code == ""
                or self.value.meaning == ""
                or self.value.scheme == ""
            ):
                return False
            if (
                self.schema.allowed_schemas is not None
                and self.value.scheme not in self.schema.allowed_schemas
            ):
                return False
            return True
        return self.schema.optional

    def _set_value(self, value: Code) -> None:
        self.updated_value = value

    def copy(self) -> CodeAttribute:
        return CodeAttribute(
            schema=self.schema,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class BooleanAttribute(Attribute[BooleanAttributeSchema, bool]):
    """An attribute defined by a tag and a boolean value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)
    updated_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)

    def __init__(
        self,
        schema: BooleanAttributeSchema,
        value: Optional[bool] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new boolean attribute.

        Parameters
        ----------
        schema: BooleanAttributeSchema
            The schema of the attribute.
        value: Optional[bool] = None
            The value of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.BOOLEAN,
    }
    __tablename__ = "boolean_attribute"

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            if self.schema is not None:
                if self.value and self.schema.true_display_value is not None:
                    return self.schema.true_display_value
                elif not self.value and self.schema.false_display_value is not None:
                    return self.schema.false_display_value
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if self.value is not None:
            return True
        return self.schema.optional

    def _set_value(self, value: bool) -> None:
        self.updated_value = value

    def copy(self) -> BooleanAttribute:
        return BooleanAttribute(
            schema=self.schema,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class ObjectAttribute(Attribute[ObjectAttributeSchema, List[Attribute]]):
    """An attribute that can have nested attributes."""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)

    # Relations
    # Attributes in the value of this attribute.
    original_value: Mapped[Dict[str, Attribute]] = db.relationship(
        Attribute,
        collection_class=attribute_mapped_collection("tag"),
        lazy=True,
        single_parent=True,
        foreign_keys=Attribute.parent_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore
    updated_value: Mapped[Dict[str, Attribute]] = db.relationship(
        Attribute,
        collection_class=attribute_mapped_collection("tag"),
        lazy=True,
        single_parent=True,
        foreign_keys=Attribute.parent_updated_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore

    def __getitem__(self, tag: str) -> Attribute[Any, Any]:
        return self.attributes[tag]

    def __init__(
        self,
        schema: ObjectAttributeSchema,
        value: Optional[Union[Sequence[Attribute], Dict[str, Attribute]]] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new object attribute.

        Parameters
        ----------
        schema: ObjectAttributeSchema
            The schema of the attribute.
        value: Optional[Union[Sequence[Attribute], Dict[str, Attribute]]] = None
            The value (attributes) of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        if value is not None:
            if not isinstance(value, dict):
                value = {attribute.tag: attribute for attribute in value}
            self._assert_schema_of_attribute(value.values(), schema)
        else:
            value = {}
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value={},
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.OBJECT,
    }
    __tablename__ = "object_attribute"

    @hybrid_property
    def attributes(self) -> Dict[str, Attribute]:
        if len(self.updated_value) > 0:
            return self.updated_value
        return self.original_value

    @hybrid_property
    def value(self) -> Dict[str, Attribute]:
        if len(self.updated_value) > 0:
            return self.updated_value
        if self.mapping is not None:
            assert isinstance(self.mapping.attribute, ObjectAttribute)
            return self.mapping.attribute.value
        return self.attributes

    def _set_display_value(self) -> Optional[str]:
        if (
            self.schema.display_value_format_string is not None
            and len(self.attributes) > 0
        ):
            format_string = self.schema.display_value_format_string
            try:
                return format_string.format(
                    **{
                        attribute.tag: attribute.display_value
                        for attribute in self.attributes.values()
                    }
                )
            except KeyError:
                current_app.logger.error(
                    f"Failed to format string {format_string} with attributes "
                    f"{self.attributes.keys()}",
                    exc_info=True,
                )
        if self.mappable_value is not None:
            return self.mappable_value
        return f"{self.schema_display_name}[{len(self.attributes)}]"

    def _validate(self) -> bool:
        if self.schema.optional:
            return True
        if len(self.attributes) == 0:
            return False
        all_children_valid = all(
            attribute.valid for attribute in self.attributes.values()
        )
        return all_children_valid

    def recursive_get_all_attributes(self, schema_uid: UUID) -> Set[Attribute]:
        attributes: Set[Attribute] = set()
        if self.schema_uid == schema_uid:
            attributes.add(self)
        for attribute in self.attributes.values():
            attributes.update(attribute.recursive_get_all_attributes(schema_uid))
        return attributes

    def _set_value(self, value: Dict[str, Attribute]) -> None:
        self._assert_schema_of_attribute(value.values(), self.schema)
        self.updated_value = value

    @staticmethod
    def _assert_schema_of_attribute(
        attributes: Iterable[Attribute[AttributeSchema, Any]],
        schema: ObjectAttributeSchema,
    ):
        missmatching = next(
            (
                attribute
                for attribute in attributes
                if attribute.schema not in schema.attributes
            ),
            None,
        )
        if missmatching is not None:
            raise NotAllowedActionError(
                "Schema of attribute must match given schemas in the "
                f"attribute schema {schema.name}. "
                f"Was {missmatching.schema.name} and not of "
                f"{', '.join([schema.name for schema in schema.attributes])}."
            )

    def copy(self) -> ObjectAttribute:
        return ObjectAttribute(
            schema=self.schema,
            value=[attribute.copy() for attribute in self.value.values()],
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class ListAttribute(Attribute[ListAttributeSchema, List[Attribute]]):
    """Attribute that can hold a list of the same type (defined by schema)."""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)

    # Relations
    # Attributes in the value of this attribute.
    original_value: Mapped[List[Attribute]] = db.relationship(
        Attribute,
        lazy=True,
        single_parent=True,
        foreign_keys=Attribute.parent_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore
    updated_value: Mapped[List[Attribute]] = db.relationship(
        Attribute,
        lazy=True,
        single_parent=True,
        foreign_keys=Attribute.parent_updated_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore

    def __iter__(self):
        return (attribute for attribute in self.attributes)

    def __init__(
        self,
        schema: ListAttributeSchema,
        value: Optional[List[Attribute]] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new list attribute.

        Parameters
        ----------
        schema: ListAttributeSchema
            The schema of the attribute.
        value: Optional[List[Attribute]] = None
            The value (attributes) of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        if value is not None:
            self._assert_schema_of_attribute(value, schema)
        else:
            value = []
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=[],
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.LIST,
    }
    __tablename__ = "attribute_list"

    def _set_display_value(self) -> Optional[str]:
        if len(self.attributes) > 0:
            display_values = [
                attribute.display_value
                if attribute.display_value is not None
                else "N/A"
                for attribute in self.attributes
            ]
            return f"[{', '.join(display_values)}]"
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if self.schema.optional:
            return True
        if len(self.attributes) == 0:
            return False
        return all(attribute.valid for attribute in self.attributes)

    @hybrid_property
    def value(self) -> List[Attribute]:
        if len(self.updated_value) > 0:
            return self.updated_value
        if self.mapping is not None:
            assert isinstance(self.mapping.attribute, ListAttribute)
            return self.mapping.attribute.value
        return self.attributes

    @hybrid_property
    def attributes(self) -> List[Attribute]:
        if len(self.updated_value) > 0:
            return self.updated_value
        return self.original_value

    def recursive_get_all_attributes(self, schema_uid: UUID) -> Set["Attribute"]:
        attributes: Set[Attribute] = set()
        if self.schema_uid == schema_uid:
            attributes.add(self)
        for attribute in self.attributes:
            attributes.update(attribute.recursive_get_all_attributes(schema_uid))

        return attributes

    def _set_value(self, value: List[Attribute]) -> None:
        self._assert_schema_of_attribute(value, self.schema)
        self.updated_value = value

    @staticmethod
    def _assert_schema_of_attribute(
        attributes: Iterable[Attribute[AttributeSchema, Any]],
        schema: ListAttributeSchema,
    ):
        missmatching = next(
            (
                attribute
                for attribute in attributes
                if attribute.schema not in schema.attributes
            ),
            None,
        )
        if missmatching is not None:
            raise NotAllowedActionError(
                "Schema of attribute must match given schemas in the list schema. "
                f"Was {missmatching.schema.name} and not of {schema.attribute.name}."
            )

    def copy(self) -> ListAttribute:
        return ListAttribute(
            schema=self.schema,
            value=[attribute.copy() for attribute in self.value],
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class UnionAttribute(Attribute[UnionAttributeSchema, Attribute]):
    """Attribute that can be of different specified (by schema) type."""

    __allow_unmapped__ = True
    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)

    # Relations
    # Attribute in the value of this attribute.
    original_value: Mapped[Optional[Attribute[Any, Any]]] = db.relationship(
        Attribute,
        lazy=True,
        single_parent=True,
        uselist=False,
        foreign_keys=Attribute.parent_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore
    updated_value: Mapped[Optional[Attribute[Any, Any]]] = db.relationship(
        Attribute,
        lazy=True,
        single_parent=True,
        uselist=False,
        foreign_keys=Attribute.parent_updated_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore

    def __init__(
        self,
        schema: UnionAttributeSchema,
        value: Optional[Attribute[Any, Any]] = None,
        mappable_value: Optional[str] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        """Create a new union attribute.

        Parameters
        ----------
        schema: UnionAttributeSchema
            The schema of the attribute.
        value: Optional[Attribute[Any, Any]] = None
            The value (attribute) of the attribute, by default None.
        mappable_value: Optional[str] = None
            The mappable value of the attribute, by default None.
        """
        if value is not None:
            self._assert_schema_of_attribute(value, schema)
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.UNION,
    }
    __tablename__ = "attribute_union"

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return self.value.display_value
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def _validate(self) -> bool:
        if self.value is not None:
            return self.value.valid
        return self.schema.optional

    @hybrid_property
    def attribute(self) -> Optional[Attribute]:
        if self.updated_value is not None:
            return self.updated_value
        return self.original_value

    @hybrid_property
    def value(self) -> Optional[Attribute]:
        """Return value. For a union attribute the value is an attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapping is not None:
            # If mapped, return the attribute of the mapping attribute.
            return self.mapping.attribute.value
        if self.attribute is not None:
            return self.attribute
        return None

    def recursive_get_all_attributes(self, schema_uid: UUID) -> Set["Attribute"]:
        attributes: Set[Attribute] = set()
        if self.schema_uid == schema_uid:
            attributes.add(self)
        if self.attribute is not None:
            attributes.update(self.attribute.recursive_get_all_attributes(schema_uid))
        return attributes

    def _set_value(self, value: Attribute) -> None:
        self._assert_schema_of_attribute(value, self.schema)
        self.updated_value = value

    @staticmethod
    def _assert_schema_of_attribute(
        attribute: Attribute[AttributeSchema, Any], schema: UnionAttributeSchema
    ):
        if attribute.schema not in schema.attributes:
            raise NotAllowedActionError(
                "Schema of attribute must match given schemas in the union schema. "
                f"Was {attribute.schema.name} and not of "
                f"{', '.join([schema.name for schema in schema.attributes])}."
            )

    def copy(self) -> UnionAttribute:
        return UnionAttribute(
            schema=self.schema,
            value=self.value.copy() if self.value is not None else None,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class MappingItem(DbBase):
    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    mapper_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("mapper.uid"))
    expression: Mapped[str] = db.Column(db.String(128))
    attribute_uid = mapped_column(db.ForeignKey("attribute.uid"))

    # Relations
    # Attributes this mapping item has mapped.
    mapped_attributes: Mapped[List[Attribute]] = db.relationship(
        Attribute,
        back_populates="mapping",
        foreign_keys=[Attribute.mapping_item_uid],
    )  # type: ignore

    # The attribute this mapping maps to.
    attribute: Mapped[Attribute] = db.relationship(
        Attribute,
        lazy=True,
        uselist=False,
        back_populates="parent_mappings",
        foreign_keys=[attribute_uid],
    )  # type: ignore

    def __init__(
        self,
        expression: str,
        attribute: Attribute,
        add: bool = True,
        commit: bool = True,
    ):
        super().__init__(
            expression=expression, attribute=attribute, add=add, commit=commit
        )

    def matches(self, mappable_value: str) -> bool:
        return re.match(self.expression, mappable_value) is not None

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def update(self, expression: str, attribute: Attribute):
        self.expression = expression
        self.attribute = attribute
        db.session.commit()

    @classmethod
    def get_by_uid(cls, uid: UUID):
        return db.session.scalars(select(cls).filter_by(uid=uid)).one()
