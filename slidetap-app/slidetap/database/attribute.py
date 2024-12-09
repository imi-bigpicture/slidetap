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

"""Attributes of different value and schema types."""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from types import MappingProxyType
from typing import (
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
)
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import Uuid, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import DbBase, NotAllowedActionError, db
from slidetap.database.schema import (
    AttributeValueType,
    DatabaseAttributeSchema,
    DatabaseAttributeSchemaType,
    DatabaseBooleanAttributeSchema,
    DatabaseCodeAttributeSchema,
    DatabaseDatetimeAttributeSchema,
    DatabaseEnumAttributeSchema,
    DatabaseListAttributeSchema,
    DatabaseMeasurementAttributeSchema,
    DatabaseNumericAttributeSchema,
    DatabaseObjectAttributeSchema,
    DatabaseStringAttributeSchema,
    DatabaseUnionAttributeSchema,
)
from slidetap.database.types import (
    attribute_db_type,
    attribute_dict_db_type,
    attribute_list_db_type,
    code_db_type,
    measurement_db_type,
)
from slidetap.model import Code, ValueStatus
from slidetap.model.attribute import (
    Attribute,
    BooleanAttribute,
    CodeAttribute,
    DatetimeAttribute,
    EnumAttribute,
    ListAttribute,
    MeasurementAttribute,
    NumericAttribute,
    ObjectAttribute,
    StringAttribute,
    UnionAttribute,
)
from slidetap.model.measurement import Measurement

ValueStorageType = TypeVar("ValueStorageType")
AttributeType = TypeVar("AttributeType", bound="Attribute")
DatabaseAttributeType = TypeVar("DatabaseAttributeType", bound="DatabaseAttribute")


class DatabaseAttribute(
    DbBase, Generic[AttributeType, DatabaseAttributeSchemaType, ValueStorageType]
):
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
    mapping_item_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("mapping_item.uid")
    )
    # Relations
    schema: Mapped[DatabaseAttributeSchemaType] = db.relationship(DatabaseAttributeSchema)  # type: ignore

    def __init__(
        self,
        schema: DatabaseAttributeSchema,
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
        if commit:
            db.session.commit()

    __mapper_args__ = {
        "polymorphic_on": "attribute_value_type",
    }
    __tablename__ = "attribute"

    @classmethod
    def get_or_create_from_model(cls, model: Attribute) -> DatabaseAttribute:
        if isinstance(model, StringAttribute):
            return DatabaseStringAttribute.get_or_create_from_model(model)
        if isinstance(model, EnumAttribute):
            return DatabaseEnumAttribute.get_or_create_from_model(model)
        if isinstance(model, DatetimeAttribute):
            return DatabaseDatetimeAttribute.get_or_create_from_model(model)
        if isinstance(model, NumericAttribute):
            return DatabaseNumericAttribute.get_or_create_from_model(model)
        if isinstance(model, MeasurementAttribute):
            return DatabaseMeasurementAttribute.get_or_create_from_model(model)
        if isinstance(model, ListAttribute):
            return DatabaseListAttribute.get_or_create_from_model(model)
        if isinstance(model, UnionAttribute):
            return DatabaseUnionAttribute.get_or_create_from_model(model)
        if isinstance(model, ObjectAttribute):
            return DatabaseObjectAttribute.get_or_create_from_model(model)
        raise ValueError(f"Unknown attribute type {type(model)}")

    @hybrid_property
    def value(self) -> ValueStorageType:
        if self.updated_value is not None:
            return self.updated_value
        return self.original_value

    @hybrid_property
    @abstractmethod
    def original_value(self) -> ValueStorageType:
        """The original value set for the attribute."""
        raise NotImplementedError()

    @hybrid_property
    @abstractmethod
    def updated_value(self) -> ValueStorageType:
        """The updated value set for the attribute."""
        raise NotImplementedError()

    @hybrid_property
    @abstractmethod
    def mapped_value(self) -> ValueStorageType:
        """The mapped value of the attribute."""
        raise NotImplementedError()

    @classmethod
    def from_model(
        cls: Type[DatabaseAttributeType], model: AttributeType
    ) -> DatabaseAttributeType:
        """Set the attribute from a model."""
        raise NotImplementedError()

    @abstractmethod
    def _set_display_value(self) -> Optional[str]:
        """Display value of the attribute."""
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
        if self.mapped_value is None:
            return ValueStatus.NOT_MAPPED
        return ValueStatus.MAPPED

    @hybrid_property
    def tag(self) -> str:
        """The tag of the attribute."""
        return self.schema.tag

    @hybrid_property
    def schema_display_name(self) -> str:
        """The display name of the attribute."""
        return self.schema.display_name

    @classmethod
    def get(cls: Type[DatabaseAttributeType], uid: UUID) -> DatabaseAttributeType:
        """Get attribute by uid.

        Parameters
        ----------
        uid: UUID
            The uid of the attribute.

        Returns
        -------
        Optional[AttributeType]
            The attribute or None if not found."""
        attribute = db.session.get(cls, uid)
        if attribute is None:
            raise ValueError(f"Attribute with uid {uid} not found.")
        return attribute

    @classmethod
    def get_optional(
        cls: Type[DatabaseAttributeType], uid: UUID
    ) -> Optional[DatabaseAttributeType]:
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

    def set_mapping(self, value: ValueStorageType, commit: bool = True) -> None:
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
        current_app.logger.debug(f"Setting mapping for attribute {self.uid} to {value}")
        self._set_mapped_value(value)
        self.display_value = self._set_display_value()
        if commit:
            db.session.commit()

    def clear_mapping(self, commit: bool = True):
        """Clear the mapping of the attribute."""
        self.mapped_value = None
        if commit:
            db.session.commit()

    def set_value(self, value: Optional[ValueStorageType], commit: bool = True) -> None:
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
        self._set_updated_value(value)
        self.display_value = self._set_display_value()
        if commit:
            db.session.commit()

    def _set_updated_value(self, value: Optional[ValueStorageType]) -> None:
        """Set the value of the attribute.

        Parameters
        ----------
        value: Optional[ValueType]
            The value to set.
        """
        self.updated_value = value

    def _set_mapped_value(self, value: Optional[ValueStorageType]) -> None:
        """Set the value of the attribute.

        Parameters
        ----------
        value: Optional[ValueType]
            The value to set.
        """
        self.mapped_value = value

    def set_mappable_value(self, value: Optional[str], commit: bool = True) -> None:
        """Set the mappable value of the attribute.

        Parameters
        ----------
        value: Optional[str]
            The mappable value to set.
        """
        self.mappable_value = value
        if commit:
            db.session.commit()

    @classmethod
    def get_for_attribute_schema(
        cls, attribute_schema_uid: UUID
    ) -> Iterable["DatabaseAttribute"]:
        return db.session.scalars(
            select(cls).filter_by(schema_uid=attribute_schema_uid)
        )

    @abstractmethod
    def copy(self) -> DatabaseAttribute:
        """Copy the attribute."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def model(self) -> Attribute:
        raise NotImplementedError()


class DatabaseStringAttribute(
    DatabaseAttribute[StringAttribute, DatabaseStringAttributeSchema, str]
):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[str] = db.Column(db.String(512))
    updated_value: Optional[str] = db.Column(db.String(512))
    mapped_value: Optional[str] = db.Column(db.String(512))

    def __init__(
        self,
        schema: DatabaseStringAttributeSchema,
        value: Optional[str] = None,
        updated_value: Optional[str] = None,
        mapped_value: Optional[str] = None,
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
            mapped_value=mapped_value,
            updated_value=updated_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.STRING,
    }
    __tablename__ = "string_attribute"

    @classmethod
    def get_or_create_from_model(
        cls, model: StringAttribute
    ) -> DatabaseStringAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseStringAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> StringAttribute:
        return StringAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    def _set_display_value(self) -> Optional[str]:
        if self.updated_value is not None:
            return self.updated_value
        if self.original_value is not None:
            return self.original_value
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def copy(self) -> DatabaseStringAttribute:
        return DatabaseStringAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseEnumAttribute(
    DatabaseAttribute[EnumAttribute, DatabaseEnumAttributeSchema, str]
):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[str] = db.Column(db.String(128))
    updated_value: Optional[str] = db.Column(db.String(128))
    mapped_value: Optional[str] = db.Column(db.String(128))

    def __init__(
        self,
        schema: DatabaseEnumAttributeSchema,
        value: Optional[str] = None,
        updated_value: Optional[str] = None,
        mapped_value: Optional[str] = None,
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
            updated_value=updated_value,
            mapped_value=mapped_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.ENUM,
    }
    __tablename__ = "enum_attribute"

    @classmethod
    def get_or_create_from_model(cls, model: EnumAttribute) -> DatabaseEnumAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseEnumAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> EnumAttribute:
        return EnumAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    def _set_display_value(self) -> Optional[str]:
        if self.updated_value is not None:
            return self.updated_value
        if self.original_value is not None:
            return self.original_value
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def copy(self) -> DatabaseEnumAttribute:
        return DatabaseEnumAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseDatetimeAttribute(
    DatabaseAttribute[DatetimeAttribute, DatabaseDatetimeAttributeSchema, datetime]
):
    """An attribute defined by a tag and a datetime value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[datetime] = db.Column(db.DateTime)
    updated_value: Optional[datetime] = db.Column(db.DateTime)
    mapped_value: Optional[datetime] = db.Column(db.DateTime)

    def __init__(
        self,
        schema: DatabaseDatetimeAttributeSchema,
        value: Optional[datetime] = None,
        updated_value: Optional[datetime] = None,
        mapped_value: Optional[datetime] = None,
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
            updated_value=updated_value,
            mapped_value=mapped_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.DATETIME,
    }
    __tablename__ = "datetime_attribute"

    @classmethod
    def get_or_create_from_model(
        cls, model: DatetimeAttribute
    ) -> DatabaseDatetimeAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseDatetimeAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> DatetimeAttribute:
        return DatetimeAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def copy(self) -> DatabaseDatetimeAttribute:
        return DatabaseDatetimeAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseNumericAttribute(
    DatabaseAttribute[NumericAttribute, DatabaseNumericAttributeSchema, float]
):
    """An attribute defined by a tag and a float value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[float] = db.Column(db.Float)
    updated_value: Optional[float] = db.Column(db.Float)
    mapped_value: Optional[float] = db.Column(db.Float)

    def __init__(
        self,
        schema: DatabaseNumericAttributeSchema,
        value: Optional[float] = None,
        updated_value: Optional[float] = None,
        mapped_value: Optional[float] = None,
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
            updated_value=updated_value,
            mapped_value=mapped_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.NUMERIC,
    }
    __tablename__ = "number_attribute"

    @classmethod
    def get_or_create_from_model(
        cls, model: NumericAttribute
    ) -> DatabaseNumericAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseNumericAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> NumericAttribute:
        return NumericAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def copy(self) -> DatabaseNumericAttribute:
        return DatabaseNumericAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseMeasurementAttribute(
    DatabaseAttribute[
        MeasurementAttribute, DatabaseMeasurementAttributeSchema, Measurement
    ]
):
    """An attribute defined by a tag and a measurement value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)
    updated_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)
    mapped_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)

    def __init__(
        self,
        schema: DatabaseMeasurementAttributeSchema,
        value: Optional[Measurement] = None,
        updated_value: Optional[Measurement] = None,
        mapped_value: Optional[Measurement] = None,
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
            updated_value=updated_value,
            mapped_value=mapped_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.MEASUREMENT,
    }
    __tablename__ = "measurement_attribute"

    @classmethod
    def get_or_create_from_model(
        cls, model: MeasurementAttribute
    ) -> DatabaseMeasurementAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseMeasurementAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> MeasurementAttribute:
        return MeasurementAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    def _set_display_value(self) -> Optional[str]:
        if self.updated_value is not None:
            return f"{self.updated_value.value} {self.updated_value.unit}"
        if self.original_value is not None:
            return f"{self.original_value.value} {self.original_value.unit}"
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def copy(self) -> DatabaseMeasurementAttribute:
        return DatabaseMeasurementAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseCodeAttribute(
    DatabaseAttribute[CodeAttribute, DatabaseCodeAttributeSchema, Code]
):
    """An attribute defined by a tag and a code value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Code]] = mapped_column(code_db_type)
    updated_value: Mapped[Optional[Code]] = mapped_column(code_db_type)
    mapped_value: Mapped[Optional[Code]] = mapped_column(code_db_type)

    def __init__(
        self,
        schema: DatabaseCodeAttributeSchema,
        value: Optional[Code] = None,
        updated_value: Optional[Code] = None,
        mapped_value: Optional[Code] = None,
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
            updated_value=updated_value,
            mapped_value=mapped_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.CODE,
    }
    __tablename__ = "code_attribute"

    @classmethod
    def get_or_create_from_model(cls, model: CodeAttribute) -> DatabaseCodeAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseCodeAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> CodeAttribute:
        return CodeAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None and self.value.meaning is not None:
            return str(self.value.meaning)
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def copy(self) -> DatabaseCodeAttribute:
        return DatabaseCodeAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseBooleanAttribute(
    DatabaseAttribute[BooleanAttribute, DatabaseBooleanAttributeSchema, bool]
):
    """An attribute defined by a tag and a boolean value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)
    updated_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)
    mapped_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)

    def __init__(
        self,
        schema: DatabaseBooleanAttributeSchema,
        value: Optional[bool] = None,
        updated_value: Optional[bool] = None,
        mapped_value: Optional[bool] = None,
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
            updated_value=updated_value,
            mapped_value=mapped_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.BOOLEAN,
    }
    __tablename__ = "boolean_attribute"

    @classmethod
    def get_or_create_from_model(
        cls, model: BooleanAttribute
    ) -> DatabaseBooleanAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseBooleanAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> BooleanAttribute:
        return BooleanAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

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

    def copy(self) -> DatabaseBooleanAttribute:
        return DatabaseBooleanAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseObjectAttribute(
    DatabaseAttribute[
        ObjectAttribute, DatabaseObjectAttributeSchema, Dict[str, Attribute]
    ]
):
    """An attribute that can have nested attributes."""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Dict[str, Attribute]]] = mapped_column(
        attribute_dict_db_type
    )
    updated_value: Mapped[Optional[Dict[str, Attribute]]] = mapped_column(
        attribute_dict_db_type
    )
    mapped_value: Mapped[Optional[Dict[str, Attribute]]] = mapped_column(
        attribute_dict_db_type
    )

    def __getitem__(self, tag: str) -> Attribute:
        if self.value is None:
            raise KeyError(tag)
        return self.value[tag]

    def __init__(
        self,
        schema: DatabaseObjectAttributeSchema,
        value: Optional[Mapping[str, Attribute]] = None,
        updated_value: Optional[Mapping[str, Attribute]] = None,
        mapped_value: Optional[Mapping[str, Attribute]] = None,
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
            self._assert_schema_of_attribute(value, schema)
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.OBJECT,
    }
    __tablename__ = "object_attribute"

    @classmethod
    def get_or_create_from_model(
        cls, model: ObjectAttribute
    ) -> DatabaseObjectAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseObjectAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> ObjectAttribute:
        return ObjectAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=(
                MappingProxyType(self.original_value) if self.original_value else None
            ),
            updated_value=(
                MappingProxyType(self.updated_value) if self.updated_value else None
            ),
            mapped_value=(
                MappingProxyType(self.mapped_value) if self.mapped_value else None
            ),
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    @hybrid_property
    def value(self) -> Optional[Dict[str, Attribute]]:
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

    def _set_display_value(self) -> Optional[str]:
        if (
            self.schema.display_value_format_string is not None
            and self.value is not None
        ):
            format_string = self.schema.display_value_format_string
            try:
                return format_string.format(
                    **{
                        tag: attribute.display_value
                        for tag, attribute in self.value.items()
                    }
                )
            except KeyError:
                current_app.logger.error(
                    f"Failed to format string {format_string} with attributes "
                    f"{self.value.keys()}",
                    exc_info=True,
                )
        if self.mappable_value is not None:
            return self.mappable_value
        return f"{self.schema_display_name}[{len(self.value or [])}]"

    def _set_updated_value(self, value: Optional[Dict[str, Attribute]]) -> None:
        if value is not None:
            self._assert_schema_of_attribute(value, self.schema)
        self.updated_value = value

    def _set_mapped_value(self, value: Dict[str, Attribute] | None) -> None:
        if value is not None:
            self._assert_schema_of_attribute(value, self.schema)
        self.mapped_value = value

    def set_original_value(self, value: Dict[str, Attribute]) -> None:
        self._assert_schema_of_attribute(value, self.schema)
        self.original_value = value
        self.display_value = self._set_display_value()

    @staticmethod
    def _assert_schema_of_attribute(
        attributes: Mapping[str, Attribute],
        schema: DatabaseObjectAttributeSchema,
    ):
        missmatching = next(
            (
                (tag, attribute)
                for tag, attribute in attributes.items()
                if tag not in schema.attributes
                or attribute.schema_uid != schema.attributes[tag].uid
            ),
            None,
        )
        if missmatching is None:
            return
        tag, attribute = missmatching
        if tag not in schema.attributes:
            raise NotAllowedActionError(
                f"Tag {tag} is not in the schema of the attribute {schema.name}."
            )
        raise NotAllowedActionError(
            "Schema of attribute must match given schemas in the attribute schema. "
            f"Was {attribute.uid} and not of {schema.attributes[tag].uid}."
        )

    def copy(self) -> DatabaseObjectAttribute:
        return DatabaseObjectAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseListAttribute(
    DatabaseAttribute[ListAttribute, DatabaseListAttributeSchema, List[Attribute]]
):
    """Attribute that can hold a list of the same type (defined by schema)."""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[List[Attribute]]] = mapped_column(
        attribute_list_db_type
    )
    updated_value: Mapped[Optional[List[Attribute]]] = mapped_column(
        attribute_list_db_type
    )
    mapped_value: Mapped[Optional[List[Attribute]]] = mapped_column(
        attribute_list_db_type
    )

    def __iter__(self):
        return (attribute for attribute in self.value) if self.value is not None else []

    def __init__(
        self,
        schema: DatabaseListAttributeSchema,
        value: Optional[Iterable[Attribute]] = None,
        updated_value: Optional[Iterable[Attribute]] = None,
        mapped_value: Optional[Iterable[Attribute]] = None,
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
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=list(value) if value is not None else None,
            updated_value=list(updated_value) if updated_value is not None else None,
            mapped_value=list(mapped_value) if mapped_value is not None else None,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.LIST,
    }
    __tablename__ = "attribute_list"

    @classmethod
    def get_or_create_from_model(cls, model: ListAttribute) -> DatabaseListAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseListAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> ListAttribute:
        return ListAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=tuple(self.original_value) if self.original_value else None,
            updated_value=tuple(self.updated_value) if self.updated_value else None,
            mapped_value=tuple(self.mapped_value) if self.mapped_value else None,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None and len(self.value) > 0:
            display_values = [
                (
                    attribute.display_value
                    if attribute.display_value is not None
                    else "N/A"
                )
                for attribute in self.value
            ]
            return f"[{', '.join(display_values)}]"
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    @hybrid_property
    def value(self) -> Optional[List[Attribute]]:
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

    def set_original_value(self, value: List[Attribute]) -> None:
        self._assert_schema_of_attribute(value, self.schema)
        self.original_value = value
        self.display_value = self._set_display_value()

    def _set_updated_value(self, value: Optional[List[Attribute]]) -> None:
        if value is not None:
            self._assert_schema_of_attribute(value, self.schema)
        self.updated_value = value

    def _set_mapped_value(self, value: Optional[List[Attribute]]) -> None:
        if value is not None:
            self._assert_schema_of_attribute(value, self.schema)
        self.mapped_value = value

    @staticmethod
    def _assert_schema_of_attribute(
        attributes: Iterable[Attribute],
        schema: DatabaseListAttributeSchema,
    ):
        missmatching = next(
            (
                attribute
                for attribute in attributes
                if attribute.schema_uid != schema.attribute.uid
            ),
            None,
        )
        if missmatching is not None:
            raise NotAllowedActionError(
                "Schema of attribute must match given schema in the list schema. "
                f"Was {missmatching.schema_uid} and not of {schema.attribute.uid}."
            )

    def copy(self) -> DatabaseListAttribute:
        return DatabaseListAttribute(
            schema=self.schema,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseUnionAttribute(
    DatabaseAttribute[UnionAttribute, DatabaseUnionAttributeSchema, Attribute]
):
    """Attribute that can be of different specified (by schema) type."""

    __allow_unmapped__ = True
    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)
    updated_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)
    mapped_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)

    def __init__(
        self,
        schema: DatabaseUnionAttributeSchema,
        value: Optional[Attribute] = None,
        updated_value: Optional[Attribute] = None,
        mapped_value: Optional[Attribute] = None,
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
            pass
        super().__init__(
            schema=schema,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            add=add,
            commit=commit,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.UNION,
    }
    __tablename__ = "attribute_union"

    @classmethod
    def get_or_create_from_model(cls, model: UnionAttribute) -> DatabaseUnionAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            schema=DatabaseUnionAttributeSchema.get(model.schema_uid),
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=False,
            commit=False,
        )

    @property
    def model(self) -> UnionAttribute:
        return UnionAttribute(
            uid=self.uid,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            valid=self.valid,
            display_value=self.display_value,
            mappable_value=self.mappable_value,
            mapping_item_uid=self.mapping_item_uid,
        )

    def _set_display_value(self) -> Optional[str]:
        if self.value is not None:
            return self.value.display_value
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    @hybrid_property
    def value(self) -> Optional[Attribute]:
        """Return value. For a union attribute the value is an attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            # If mapped, return the attribute of the mapping attribute.
            return self.mapped_value
        return self.original_value

    def _set_updated_value(self, value: Optional[Attribute]) -> None:
        if value is not None:
            self._assert_schema_of_attribute(value, self.schema)
        self.updated_value = value

    def _set_mapped_value(self, value: Optional[Attribute]) -> None:
        if value is not None:
            self._assert_schema_of_attribute(value, self.schema)
        self.mapped_value = value

    def set_original_value(self, value: Attribute) -> None:
        self._assert_schema_of_attribute(value, self.schema)
        self.original_value = value
        self.display_value = self._set_display_value()

    @staticmethod
    def _assert_schema_of_attribute(
        attribute: Attribute,
        schema: DatabaseUnionAttributeSchema,
    ):
        if attribute.schema_uid not in schema.attributes:
            raise NotAllowedActionError(
                "Schema of attribute must match given schemas in the union schema. "
                f"Was {attribute} and not of {', '.join(str(schema_uid) for schema_uid in schema.attributes.keys())}."
            )

    def copy(self) -> DatabaseUnionAttribute:
        return DatabaseUnionAttribute(
            schema=self.schema,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )
