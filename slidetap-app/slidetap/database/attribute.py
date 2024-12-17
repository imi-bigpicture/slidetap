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
    Type,
    TypeVar,
)
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import UniqueConstraint, Uuid, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import DbBase, NotAllowedActionError, db
from slidetap.database.types import (
    attribute_db_type,
    attribute_dict_db_type,
    attribute_list_db_type,
    code_db_type,
    measurement_db_type,
)
from slidetap.model import (
    Attribute,
    AttributeValueType,
    BooleanAttribute,
    Code,
    CodeAttribute,
    DatetimeAttribute,
    EnumAttribute,
    ListAttribute,
    Measurement,
    MeasurementAttribute,
    NumericAttribute,
    ObjectAttribute,
    StringAttribute,
    UnionAttribute,
)
from slidetap.model.schema.attribute_schema import AttributeSchema

ValueStorageType = TypeVar("ValueStorageType")
AttributeType = TypeVar("AttributeType", bound="Attribute")
DatabaseAttributeType = TypeVar("DatabaseAttributeType", bound="DatabaseAttribute")


class DatabaseAttribute(DbBase, Generic[AttributeType, ValueStorageType]):
    """An attribute defined by a tag and a value"""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    tag: Mapped[str] = db.Column(db.String(128), index=True)
    mappable_value: Mapped[Optional[str]] = db.Column(db.String(512))
    valid: Mapped[bool] = db.Column(db.Boolean)
    display_value: Mapped[Optional[str]] = db.Column(db.String(512))
    attribute_value_type: Mapped[AttributeValueType] = db.Column(
        db.Enum(AttributeValueType), index=True
    )
    read_only: Mapped[bool] = db.Column(db.Boolean, default=False)

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid)
    item_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("item.uid"), index=True
    )
    project_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("project.uid"), index=True
    )
    mapping_item_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("mapping_item.uid"), index=True
    )
    __table_args__ = (
        UniqueConstraint("schema_uid", "item_uid", "project_uid", "mapping_item_uid"),
    )

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        mappable_value: Optional[str] = None,
        read_only: bool = False,
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
            tag=tag,
            schema_uid=schema_uid,
            mappable_value=mappable_value,
            read_only=read_only,
            uid=uid if uid != UUID(int=0) else uuid4(),
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
    def get_or_create_from_model(
        cls,
        model: Attribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseAttribute:
        if isinstance(model, StringAttribute):
            return DatabaseStringAttribute.get_or_create_from_model(
                model, schema, add, commit
            )
        if isinstance(model, EnumAttribute):
            return DatabaseEnumAttribute.get_or_create_from_model(
                model, schema, add, commit
            )
        if isinstance(model, DatetimeAttribute):
            return DatabaseDatetimeAttribute.get_or_create_from_model(
                model, schema, add, commit
            )
        if isinstance(model, NumericAttribute):
            return DatabaseNumericAttribute.get_or_create_from_model(
                model, schema, add, commit
            )
        if isinstance(model, MeasurementAttribute):
            return DatabaseMeasurementAttribute.get_or_create_from_model(
                model, schema, add, commit
            )
        if isinstance(model, ListAttribute):
            return DatabaseListAttribute.get_or_create_from_model(
                model, schema, add, commit
            )
        if isinstance(model, UnionAttribute):
            return DatabaseUnionAttribute.get_or_create_from_model(
                model, schema, add, commit
            )
        if isinstance(model, ObjectAttribute):
            return DatabaseObjectAttribute.get_or_create_from_model(
                model, schema, add, commit
            )
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

    @abstractmethod
    def _set_display_value(self) -> Optional[str]:
        """Display value of the attribute."""
        raise NotImplementedError()

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
        if self.read_only:
            raise NotAllowedActionError(
                f"Cannot set mapping of read only attribute {self.tag}."
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
        if self.read_only and value != self.value:
            raise NotAllowedActionError(
                f"Cannot set value of read only attribute {self.tag}."
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


class DatabaseStringAttribute(DatabaseAttribute[StringAttribute, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[str] = db.Column(db.String(512))
    updated_value: Optional[str] = db.Column(db.String(512))
    mapped_value: Optional[str] = db.Column(db.String(512))

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
            tag=tag,
            schema_uid=schema_uid,
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
        cls,
        model: StringAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseStringAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseEnumAttribute(DatabaseAttribute[EnumAttribute, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[str] = db.Column(db.String(128))
    updated_value: Optional[str] = db.Column(db.String(128))
    mapped_value: Optional[str] = db.Column(db.String(128))

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
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
    def get_or_create_from_model(
        cls,
        model: EnumAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseEnumAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseDatetimeAttribute(DatabaseAttribute[DatetimeAttribute, datetime]):
    """An attribute defined by a tag and a datetime value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[datetime] = db.Column(db.DateTime)
    updated_value: Optional[datetime] = db.Column(db.DateTime)
    mapped_value: Optional[datetime] = db.Column(db.DateTime)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
            tag=tag,
            schema_uid=schema_uid,
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
        cls,
        model: DatetimeAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseDatetimeAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseNumericAttribute(DatabaseAttribute[NumericAttribute, float]):
    """An attribute defined by a tag and a float value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Optional[float] = db.Column(db.Float)
    updated_value: Optional[float] = db.Column(db.Float)
    mapped_value: Optional[float] = db.Column(db.Float)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
            tag=tag,
            schema_uid=schema_uid,
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
        cls,
        model: NumericAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseNumericAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseMeasurementAttribute(
    DatabaseAttribute[MeasurementAttribute, Measurement]
):
    """An attribute defined by a tag and a measurement value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)
    updated_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)
    mapped_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
            tag=tag,
            schema_uid=schema_uid,
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
        cls,
        model: MeasurementAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseMeasurementAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseCodeAttribute(DatabaseAttribute[CodeAttribute, Code]):
    """An attribute defined by a tag and a code value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Code]] = mapped_column(code_db_type)
    updated_value: Mapped[Optional[Code]] = mapped_column(code_db_type)
    mapped_value: Mapped[Optional[Code]] = mapped_column(code_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
            tag=tag,
            schema_uid=schema_uid,
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
    def get_or_create_from_model(
        cls,
        model: CodeAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseCodeAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseBooleanAttribute(DatabaseAttribute[BooleanAttribute, bool]):
    """An attribute defined by a tag and a boolean value"""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)
    updated_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)
    mapped_value: Mapped[Optional[Optional[bool]]] = db.Column(db.Boolean)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
            tag=tag,
            schema_uid=schema_uid,
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
        cls,
        model: BooleanAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseBooleanAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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
            return str(self.value)
        if self.mappable_value is not None:
            return self.mappable_value
        return None

    def copy(self) -> DatabaseBooleanAttribute:
        return DatabaseBooleanAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseObjectAttribute(DatabaseAttribute[ObjectAttribute, Dict[str, Attribute]]):
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
    display_value_format_string: Mapped[Optional[str]] = db.Column(db.String(512))

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        value: Optional[Mapping[str, Attribute]] = None,
        updated_value: Optional[Mapping[str, Attribute]] = None,
        mapped_value: Optional[Mapping[str, Attribute]] = None,
        mappable_value: Optional[str] = None,
        display_value_format_string: Optional[str] = None,
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
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            mappable_value=mappable_value,
            original_value=value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            display_value_format_string=display_value_format_string,
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
        cls,
        model: ObjectAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseObjectAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=dict(model.original_value) if model.original_value else None,
            updated_value=dict(model.updated_value) if model.updated_value else None,
            mapped_value=dict(model.mapped_value) if model.mapped_value else None,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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

    @property
    def value(self) -> Optional[Dict[str, Attribute]]:
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

    def _set_display_value(self) -> Optional[str]:
        if self.display_value_format_string is not None and self.value is not None:
            format_string = self.display_value_format_string
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
        return f"{self.tag}[{len(self.value or [])}]"

    def _set_updated_value(self, value: Optional[Dict[str, Attribute]]) -> None:
        self.updated_value = value

    def _set_mapped_value(self, value: Dict[str, Attribute] | None) -> None:
        self.mapped_value = value

    def set_original_value(self, value: Dict[str, Attribute]) -> None:
        self.original_value = value
        self.display_value = self._set_display_value()

    def copy(self) -> DatabaseObjectAttribute:
        return DatabaseObjectAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            display_value_format_string=self.display_value_format_string,
            add=False,
            commit=False,
        )


class DatabaseListAttribute(DatabaseAttribute[ListAttribute, List[Attribute]]):
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

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
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
    def get_or_create_from_model(
        cls,
        model: ListAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseListAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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

    @property
    def value(self) -> Optional[List[Attribute]]:
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

    def set_original_value(self, value: List[Attribute]) -> None:
        self.original_value = value
        self.display_value = self._set_display_value()

    def _set_updated_value(self, value: Optional[List[Attribute]]) -> None:
        self.updated_value = value

    def _set_mapped_value(self, value: Optional[List[Attribute]]) -> None:
        self.mapped_value = value

    def copy(self) -> DatabaseListAttribute:
        return DatabaseListAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )


class DatabaseUnionAttribute(DatabaseAttribute[UnionAttribute, Attribute]):
    """Attribute that can be of different specified (by schema) type."""

    __allow_unmapped__ = True
    uid: Mapped[UUID] = mapped_column(db.ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)
    updated_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)
    mapped_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
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
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
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
    def get_or_create_from_model(
        cls,
        model: UnionAttribute,
        schema: AttributeSchema,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseUnionAttribute:
        existing = cls.get_optional(model.uid)
        if existing is not None:
            return existing
        return cls(
            tag=schema.tag,
            schema_uid=schema.uid,
            value=model.original_value,
            updated_value=model.updated_value,
            mapped_value=model.mapped_value,
            mappable_value=model.mappable_value,
            uid=model.uid,
            add=add,
            commit=commit,
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

    @property
    def value(self) -> Optional[Attribute]:
        """Return value. For a union attribute the value is an attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            # If mapped, return the attribute of the mapping attribute.
            return self.mapped_value
        return self.original_value

    def _set_updated_value(self, value: Optional[Attribute]) -> None:
        self.updated_value = value

    def _set_mapped_value(self, value: Optional[Attribute]) -> None:
        self.mapped_value = value

    def set_original_value(self, value: Attribute) -> None:
        self.original_value = value
        self.display_value = self._set_display_value()

    def copy(self) -> DatabaseUnionAttribute:
        return DatabaseUnionAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            value=self.original_value,
            updated_value=self.updated_value,
            mappable_value=self.mappable_value,
            add=False,
            commit=False,
        )
