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

from slides.database.db import NotAllowedActionError, db
from slides.database.schema import (
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
from slides.model import Code, MappingStatus
from slides.model.code import Code
from slides.model.measurement import Measurement
from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.collections import attribute_mapped_collection

ValueType = TypeVar("ValueType")
AttributeType = TypeVar("AttributeType", bound="Attribute")

# TODO validation of value to match given schema (with limitations)


class Attribute(db.Model, Generic[AttributeSchemaType, ValueType]):
    """An attribute defined by a tag and a value"""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    mappable_value: Mapped[Optional[str]] = db.Column(db.String(128))
    attribute_value_type: Mapped[AttributeValueType] = db.Column(
        db.Enum(AttributeValueType)
    )

    # For relations
    parent_attribute_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("attribute.uid")
    )
    item_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("item.uid"))
    parent_mapping_item_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("mapping_item.uid")
    )
    mapping_item_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("mapping_item.uid")
    )
    schema_uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute_schema.uid"))

    # Relations
    schema: Mapped[AttributeSchemaType] = db.relationship(AttributeSchema)  # type: ignore
    mapping: Mapped[Optional[MappingItem]] = db.relationship(
        "MappingItem",
        back_populates="mapped_attributes",
        foreign_keys=[mapping_item_uid],
    )  # type: ignore
    parent_mapping: Mapped[Optional[MappingItem]] = db.relationship(
        "MappingItem",
        back_populates="attribute",
        foreign_keys=[parent_mapping_item_uid],
    )  # type: ignore

    def __init__(
        self,
        schema: AttributeSchema,
        mappable_value: Optional[str] = None,
        add: bool = True,
        **kwargs,
    ):
        super().__init__(schema=schema, mappable_value=mappable_value, **kwargs)
        if add:
            db.session.add(self)
            db.session.commit()

    __mapper_args__ = {
        "polymorphic_on": "attribute_value_type",
    }

    @property
    def value(self) -> Optional[ValueType]:
        if self.mapping is not None:
            return self.mapping.attribute.value
        if self.original_value is not None:
            return self.original_value
        return None

    @property
    @abstractmethod
    def original_value(self) -> Optional[ValueType]:
        raise NotImplementedError()

    @property
    @abstractmethod
    def display_value(self) -> str:
        raise NotImplementedError()

    @property
    def mapping_status(self) -> MappingStatus:
        if self.mappable_value is None:
            return MappingStatus.NO_MAPPABLE_VALUE
        if self.mapping_item_uid is not None:
            return MappingStatus.MAPPED
        return MappingStatus.NOT_MAPPED

    @property
    def tag(self) -> str:
        return self.schema.tag

    @property
    def schema_display_name(self) -> str:
        return self.schema.display_name

    @classmethod
    def get(cls: Type[AttributeType], uid: UUID) -> Optional[AttributeType]:
        return db.session.get(cls, uid)

    def set_mapping(self, mapping: MappingItem) -> None:
        # mapping.mapped_attributes.append(self)
        self.mapping = mapping
        db.session.commit()

    def clear_mapping(self):
        self.mapping = None
        db.session.commit()

    @abstractmethod
    def set_value(self, value: Optional[ValueType]) -> None:
        raise NotImplementedError()

    def set_mappable_value(self, value: Optional[str]) -> None:
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


class StringAttribute(Attribute[StringAttributeSchema, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[str] = db.Column(db.String(128))

    def __init__(
        self,
        schema: StringAttributeSchema,
        value: Optional[str] = None,
        mappable_value: Optional[str] = None,
    ):
        super().__init__(
            schema=schema, mappable_value=mappable_value, original_value=value
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.STRING,
    }
    __tablename__ = "string_attribute"

    @property
    def display_value(self) -> str:
        if self.value is not None:
            return self.value
        if self.mappable_value is not None:
            return self.mappable_value
        return "N/A"

    def set_value(self, value: str) -> None:
        self.original_value = value
        self.mapper_uid = None
        db.session.commit()


class EnumAttribute(Attribute[EnumAttributeSchema, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[str] = db.Column(db.String(128))

    def __init__(
        self,
        schema: EnumAttributeSchema,
        value: Optional[str] = None,
        mappable_value: Optional[str] = None,
    ):
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
            schema=schema, mappable_value=mappable_value, original_value=value
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.ENUM,
    }
    __tablename__ = "enum_attribute"

    @property
    def display_value(self) -> str:
        if self.value is not None:
            return self.value
        if self.mappable_value is not None:
            return self.mappable_value
        return "N/A"

    def set_value(self, value: str) -> None:
        self.original_value = value
        self.mapper_uid = None
        db.session.commit()


class DatetimeAttribute(Attribute[DatetimeAttributeSchema, datetime]):
    """An attribute defined by a tag and a datetime value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[datetime] = db.Column(db.DateTime)

    def __init__(
        self,
        schema: DatetimeAttributeSchema,
        value: Optional[datetime] = None,
        mappable_value: Optional[str] = None,
    ):
        super().__init__(
            schema=schema, mappable_value=mappable_value, original_value=value
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.DATETIME,
    }
    __tablename__ = "datetime_attribute"

    @property
    def display_value(self) -> str:
        if self.value is not None:
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return "N/A"

    def set_value(self, value: datetime) -> None:
        self.original_value = value
        self.mapper_uid = None
        db.session.commit()


class NumericAttribute(Attribute[NumericAttributeSchema, Union[int, float]]):
    """An attribute defined by a tag and a float value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[float] = db.Column(db.Float)

    def __init__(
        self,
        schema: NumericAttributeSchema,
        value: Optional[float] = None,
        mappable_value: Optional[str] = None,
    ):
        super().__init__(
            schema=schema, mappable_value=mappable_value, original_value=value
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.NUMERIC,
    }
    __tablename__ = "number_attribute"

    @property
    def display_value(self) -> str:
        if self.value is not None:
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return "N/A"

    def set_value(self, value: float) -> None:
        self.original_value = value
        self.mapper_uid = None
        db.session.commit()


class MeasurementAttribute(Attribute[MeasurementAttributeSchema, Measurement]):
    """An attribute defined by a tag and a measurement value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Measurement]] = db.Column(db.PickleType)

    def __init__(
        self,
        schema: MeasurementAttributeSchema,
        value: Optional[Measurement] = None,
        mappable_value: Optional[str] = None,
    ):
        super().__init__(
            schema=schema, mappable_value=mappable_value, original_value=value
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.MEASUREMENT,
    }
    __tablename__ = "measurement_attribute"

    @property
    def display_value(self) -> str:
        if self.value is not None:
            return f"{self.value} {self.value.unit}"
        if self.mappable_value is not None:
            return self.mappable_value
        return "N/A"

    def set_value(self, value: Measurement) -> None:
        self.original_value = value
        self.mapper_uid = None
        db.session.commit()


class CodeAttribute(Attribute[CodeAttributeSchema, Code]):
    """An attribute defined by a tag and a code value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Code]] = db.Column(db.PickleType)

    def __init__(
        self,
        schema: CodeAttributeSchema,
        value: Optional[Code] = None,
        mappable_value: Optional[str] = None,
    ):
        super().__init__(
            schema=schema, mappable_value=mappable_value, original_value=value
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.CODE,
    }
    __tablename__ = "code_attribute"

    @property
    def display_value(self) -> str:
        if self.value is not None and self.value.meaning is not None:
            return str(self.value.meaning)
        if self.mappable_value is not None:
            return self.mappable_value
        return "N/A"

    def set_value(self, value: Code) -> None:
        self.original_value = value
        self.mapper_uid = None
        db.session.commit()


class BooleanAttribute(Attribute[BooleanAttributeSchema, bool]):
    """An attribute defined by a tag and a boolean value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)

    def __init__(
        self,
        schema: BooleanAttributeSchema,
        value: Optional[bool] = None,
        mappable_value: Optional[str] = None,
    ):
        super().__init__(
            schema=schema, mappable_value=mappable_value, original_value=value
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.BOOLEAN,
    }
    __tablename__ = "boolean_attribute"

    @property
    def display_value(self) -> str:
        if self.value is not None:
            if self.schema is not None:
                if self.value and self.schema.true_display_value is not None:
                    return self.schema.true_display_value
                elif not self.value and self.schema.false_display_value is not None:
                    return self.schema.false_display_value
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return "N/A"

    def set_value(self, value: bool) -> None:
        self.original_value = value
        self.mapper_uid = None
        db.session.commit()


class ObjectAttribute(Attribute[ObjectAttributeSchema, List[Attribute]]):
    """An attribute that can have nested attributes."""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    _display_value: Mapped[str] = db.Column(db.String(128))

    attributes: Mapped[Dict[str, Attribute]] = db.relationship(
        Attribute,
        collection_class=attribute_mapped_collection("tag"),
        lazy=True,
        single_parent=True,
        foreign_keys=Attribute.parent_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore

    def __getitem__(self, tag: str) -> Attribute[Any, Any]:
        return self.attributes[tag]

    def __init__(
        self,
        schema: ObjectAttributeSchema,
        attributes: Optional[Union[Sequence[Attribute], Dict[str, Attribute]]] = None,
        mappable_value: Optional[str] = None,
    ):
        if attributes is None:
            attributes = {}
        elif not isinstance(attributes, dict):
            attributes = {attribute.tag: attribute for attribute in attributes}
        self._assert_schema_of_attribute(attributes.values(), schema)
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            attributes=attributes,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.OBJECT,
    }
    __tablename__ = "object_attribute"

    @property
    def display_value(self) -> str:
        if self._display_value is not None:
            return self._display_value
        if self.mappable_value is not None:
            return self.mappable_value
        return f"({len(self.attributes)})"

    @property
    def original_value(self) -> Any:
        return self.attributes

    def recursive_get_all_attributes(self, schema_uid: UUID) -> Set[Attribute]:
        attributes: Set[Attribute] = set()
        if self.schema_uid == schema_uid:
            attributes.add(self)
        for attribute in self.attributes.values():
            attributes.update(attribute.recursive_get_all_attributes(schema_uid))
        return attributes

    def set_value(self, value: Dict[str, Attribute]) -> None:
        self._assert_schema_of_attribute(value.values(), self.schema)
        self.attributes = value
        self.mapper_uid = None
        db.session.commit()

    @staticmethod
    def _assert_schema_of_attribute(
        attributes: Iterable[Attribute[AttributeSchema, Any]],
        schema: ObjectAttributeSchema,
    ):
        for attribute in attributes:
            if (
                schema.attributes is not None
                and len(schema.attributes) != 0
                and attribute.schema not in schema.attributes
            ):
                raise NotAllowedActionError(
                    "Schema of attribute must match given schemas in the attribute schema. "
                    f"Was {attribute.schema.name} and not of "
                    f"{', '.join([schema.name for schema in schema.attributes])}."
                )


class ListAttribute(Attribute[ListAttributeSchema, List[Attribute]]):
    """Attribute that can hold a list of the same type (defined by schema)."""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)

    attributes: Mapped[List[Attribute]] = db.relationship(
        Attribute,
        lazy=True,
        single_parent=True,
        foreign_keys=Attribute.parent_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore

    def __iter__(self):
        return (attribute for attribute in self.attributes)

    def __init__(
        self,
        schema: ListAttributeSchema,
        attributes: Optional[List[Attribute]] = None,
        mappable_value: Optional[str] = None,
    ):
        if attributes is None:
            attributes = []
        self._assert_schema_of_attribute(attributes, schema)
        super().__init__(
            schema=schema, mappable_value=mappable_value, attributes=attributes
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.LIST,
    }
    __tablename__ = "attribute_list"

    @property
    def display_value(self) -> str:
        if self.mappable_value is not None:
            return self.mappable_value
        return f"({len(self.attributes)})"

    @property
    def original_value(self) -> Any:
        return self.attributes

    def recursive_get_all_attributes(self, schema_uid: UUID) -> Set["Attribute"]:
        attributes: Set[Attribute] = set()
        if self.schema_uid == schema_uid:
            attributes.add(self)
        for attribute in self.attributes:
            attributes.update(attribute.recursive_get_all_attributes(schema_uid))
        return attributes

    def set_value(self, value: List[Attribute]) -> None:
        self._assert_schema_of_attribute(value, self.schema)
        self.attributes = value
        self.mapper_uid = None
        db.session.commit()

    @staticmethod
    def _assert_schema_of_attribute(
        attributes: Iterable[Attribute[AttributeSchema, Any]],
        schema: ListAttributeSchema,
    ):
        for attribute in attributes:
            if not attribute.schema == schema.attribute:
                raise NotAllowedActionError(
                    "Schema of attribute must match given schemas in the union schema. "
                    f"Was {attribute.schema.name} and not of {schema.attribute.name}."
                )


class UnionAttribute(Attribute[UnionAttributeSchema, Attribute]):
    """Attribute that can be of different specified (by schema) type."""

    __allow_unmapped__ = True
    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    attribute: Mapped[Optional[Attribute[Any, Any]]] = db.relationship(
        Attribute,
        lazy=True,
        single_parent=True,
        uselist=False,
        foreign_keys=Attribute.parent_attribute_uid,
        cascade="all, delete-orphan",
    )  # type: ignore

    def __init__(
        self,
        schema: UnionAttributeSchema,
        attribute: Optional[Attribute[Any, Any]] = None,
        mappable_value: Optional[str] = None,
    ):
        if attribute is not None:
            self._assert_schema_of_attribute(attribute, schema)
        super().__init__(
            schema=schema, mappable_value=mappable_value, attribute=attribute
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.UNION,
    }
    __tablename__ = "attribute_union"

    @property
    def display_value(self) -> str:
        if self.value is not None:
            return self.value
        if self.mappable_value is not None:
            return self.mappable_value
        return "N/A"

    @property
    def value(self) -> Attribute:
        if self.mapping is not None:
            return self.mapping.attribute.value
        if self.attribute is not None:
            return self.attribute
        return None

    def recursive_get_all_attributes(self, schema_uid: UUID) -> Set["Attribute"]:
        attributes: Set[Attribute] = set()
        if self.schema_uid == schema_uid:
            attributes.add(self)
        if not self.attribute is None:
            attributes.update(self.attribute.recursive_get_all_attributes(schema_uid))
        return attributes

    def set_value(self, value: Attribute) -> None:
        self._assert_schema_of_attribute(value, self.schema)
        self.attribute = value
        self.mapper_uid = None
        db.session.commit()

    @staticmethod
    def _assert_schema_of_attribute(
        attribute: Attribute[AttributeSchema, Any], schema: UnionAttributeSchema
    ):
        if not attribute.schema in schema.attributes:
            raise NotAllowedActionError(
                "Schema of attribute must match given schemas in the union schema. "
                f"Was {attribute.schema.name} and not of "
                f"{', '.join([schema.name for schema in schema.attributes])}."
            )


class MappingItem(db.Model):
    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    mapper_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("mapper.uid"))
    expression: Mapped[str] = db.Column(db.String(128))
    # attribute_uid = mapped_column(db.ForeignKey("attribute.uid"))

    # Relations
    mapped_attributes: Mapped[List[Attribute]] = db.relationship(
        Attribute,
        back_populates="mapping",
        foreign_keys=[Attribute.mapping_item_uid],
    )  # type: ignore
    attribute: Mapped[Attribute] = db.relationship(
        Attribute,
        lazy=True,
        single_parent=True,
        uselist=False,
        back_populates="parent_mapping",
        foreign_keys=[Attribute.parent_mapping_item_uid],
    )  # type: ignore

    def __init__(self, expression: str, attribute: Attribute):
        super().__init__(expression=expression, attribute=attribute)
        db.session.add(self)
        db.session.commit()

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
