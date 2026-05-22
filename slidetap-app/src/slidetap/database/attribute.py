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

import logging
from abc import abstractmethod
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import (
    Generic,
    TypeVar,
)
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from slidetap.database.db import Base, NotAllowedActionError
from slidetap.database.types import (
    attribute_db_type,
    attribute_dict_db_type,
    attribute_list_db_type,
    code_db_type,
    measurement_db_type,
)
from slidetap.model import (
    AnyAttribute,
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

ValueStorageType = TypeVar("ValueStorageType")
AttributeType = TypeVar("AttributeType", bound="Attribute")
DatabaseAttributeType = TypeVar("DatabaseAttributeType", bound="DatabaseAttribute")


class DatabaseAttribute(Base, Generic[AttributeType, ValueStorageType]):
    """An attribute defined by a tag and a value"""

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    schema_uid: Mapped[UUID] = mapped_column(Uuid)
    valid: Mapped[bool] = mapped_column(Boolean, default=False)
    display_value: Mapped[str | None] = mapped_column(String())
    mappable_value: Mapped[str | None] = mapped_column(String(512))

    tag: Mapped[str] = mapped_column(String(128), index=True)
    attribute_value_type: Mapped[AttributeValueType] = mapped_column(
        Enum(AttributeValueType), index=True
    )
    read_only: Mapped[bool] = mapped_column(Boolean, default=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)

    # For relations
    attribute_item_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("item.uid"), index=True
    )
    private_attribute_item_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("item.uid"), index=True
    )
    attribute_project_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("project.uid"), index=True
    )
    private_attribute_project_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("project.uid"), index=True
    )
    attribute_dataset_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("dataset.uid"), index=True
    )
    private_attribute_dataset_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("dataset.uid"), index=True
    )
    mapping_item_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("mapping_item.uid"), index=True
    )
    __table_args__ = (
        UniqueConstraint(
            "schema_uid",
            "attribute_item_uid",
            "private_attribute_item_uid",
            "attribute_project_uid",
            "private_attribute_project_uid",
            "attribute_dataset_uid",
            "private_attribute_dataset_uid",
            "mapping_item_uid",
        ),
    )

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        valid: bool,
        mappable_value: str | None,
        display_value: str | None,
        read_only: bool = False,
        uid: UUID | None = None,
        **kwargs,
    ):
        """Create a new attribute.

        Parameters
        ----------
        schema: AttributeSchema
            The schema of the attribute.
        mappable_value: str | None = None
            The mappable value, by default None.

            Whether to commit the attribute to the database, by default False.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            read_only=read_only,
            uid=uid if (uid and uid != UUID(int=0)) else uuid4(),
            **kwargs,
        )

    __mapper_args__ = {
        "polymorphic_on": "attribute_value_type",
    }
    __tablename__ = "attribute"

    def set_mapping_item_uid(self, mapping_item_uid: UUID | None) -> None:
        """Set the mapping item UID of the attribute.

        Parameters
        ----------
        mapping_item_uid: UUID | None
            The mapping item UID to set.
        """
        self._raise_if_not_editable()
        self.mapping_item_uid = mapping_item_uid

    def set_mapped_value(
        self,
        value: ValueStorageType,
    ) -> None:
        """Set the mapped value of the attribute.

        Parameters
        ----------
        mapping: MappingItem
            The mapping to set.
        """
        self._raise_if_not_editable()
        logging.getLogger(__name__).debug(
            f"Setting mapping for attribute {self.uid} to {value}"
        )
        self.mapped_value = value

    def clear_mapping(
        self,
    ):
        """Clear the mapping of the attribute."""
        self._raise_if_not_editable()
        self.mapping_item_uid = None
        self.mapped_value = None

    def set_value(
        self,
        value: ValueStorageType | None,
        display_value: str | None,
    ) -> None:
        """Set the value of the attribute.

        Parameters
        ----------
        value: ValueType | None
            The value to set.
        """
        if self.read_only and value != self.original_value:
            raise NotAllowedActionError(
                f"Cannot set value of read only attribute {self.tag}."
            )
        self.updated_value = value
        self.display_value = display_value

    def set_mappable_value(self, value: str | None) -> None:
        """Set the mappable value of the attribute.

        Parameters
        ----------
        value: str | None
            The mappable value to set.
        """
        self._raise_if_not_editable()
        self.mappable_value = value

    def set_original_value(
        self, value: ValueStorageType | None, display_value: str | None
    ):
        """Set the original value of the attribute.

        Parameters
        ----------
        value: ValueType | None
            The value to set.
        """
        self._raise_if_not_editable()
        self.original_value = value
        self.display_value = display_value

    @abstractmethod
    def copy(self) -> DatabaseAttribute:
        """Copy the attribute."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def model(self) -> AnyAttribute:
        raise NotImplementedError()

    def _raise_if_not_editable(self):
        if self.read_only:
            raise NotAllowedActionError(f"Cannot edit read only attribute {self.tag}.")
        if self.locked:
            raise NotAllowedActionError(f"Cannot edit locked attribute {self.tag}.")


class DatabaseStringAttribute(DatabaseAttribute[StringAttribute, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[str | None] = mapped_column(String())
    updated_value: Mapped[str | None] = mapped_column(String())
    mapped_value: Mapped[str | None] = mapped_column(String())

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: str | None = None,
        updated_value: str | None = None,
        mapped_value: str | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new string attribute.

        Parameters
        ----------
        schema: StringAttributeSchema
            The schema of the attribute.
        value: str | None = None
            The value of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=original_value,
            mapped_value=mapped_value,
            updated_value=updated_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.STRING,
    }
    __tablename__ = "string_attribute"

    @property
    def value(self) -> str | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

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

    def copy(self) -> DatabaseStringAttribute:
        return DatabaseStringAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseEnumAttribute(DatabaseAttribute[EnumAttribute, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[str | None] = mapped_column(String(128))
    updated_value: Mapped[str | None] = mapped_column(String(128))
    mapped_value: Mapped[str | None] = mapped_column(String(128))

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: str | None = None,
        updated_value: str | None = None,
        mapped_value: str | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new enum attribute.

        Parameters
        ----------
        schema: EnumAttributeSchema
            The schema of the attribute.
        value: str | None = None
            The value of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.ENUM,
    }
    __tablename__ = "enum_attribute"

    @property
    def value(self) -> str | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

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

    def copy(self) -> DatabaseEnumAttribute:
        return DatabaseEnumAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseDatetimeAttribute(DatabaseAttribute[DatetimeAttribute, datetime]):
    """An attribute defined by a tag and a datetime value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[datetime | None] = mapped_column(DateTime)
    updated_value: Mapped[datetime | None] = mapped_column(DateTime)
    mapped_value: Mapped[datetime | None] = mapped_column(DateTime)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: datetime | None = None,
        updated_value: datetime | None = None,
        mapped_value: datetime | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new datetime attribute.

        Parameters
        ----------
        schema: DatetimeAttributeSchema
            The schema of the attribute.
        value: datetime | None = None
            The value of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.DATETIME,
    }
    __tablename__ = "datetime_attribute"

    @property
    def value(self) -> datetime | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

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

    def copy(self) -> DatabaseDatetimeAttribute:
        return DatabaseDatetimeAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseNumericAttribute(DatabaseAttribute[NumericAttribute, float]):
    """An attribute defined by a tag and a float value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[float | None] = mapped_column(Float)
    updated_value: Mapped[float | None] = mapped_column(Float)
    mapped_value: Mapped[float | None] = mapped_column(Float)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: float | None = None,
        updated_value: float | None = None,
        mapped_value: float | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new numeric attribute.

        Parameters
        ----------
        schema: NumericAttributeSchema
            The schema of the attribute.
        value: float | None = None
            The value of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.NUMERIC,
    }
    __tablename__ = "number_attribute"

    @property
    def value(self) -> float | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

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

    def copy(self) -> DatabaseNumericAttribute:
        return DatabaseNumericAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseMeasurementAttribute(
    DatabaseAttribute[MeasurementAttribute, Measurement]
):
    """An attribute defined by a tag and a measurement value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Measurement | None] = mapped_column(measurement_db_type)
    updated_value: Mapped[Measurement | None] = mapped_column(measurement_db_type)
    mapped_value: Mapped[Measurement | None] = mapped_column(measurement_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Measurement | None = None,
        updated_value: Measurement | None = None,
        mapped_value: Measurement | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new measurement attribute.

        Parameters
        ----------
        schema: MeasurementAttributeSchema
            The schema of the attribute.
        value: Measurement | None = None
            The value of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.MEASUREMENT,
    }
    __tablename__ = "measurement_attribute"

    @property
    def value(self) -> Measurement | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

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

    def copy(self) -> DatabaseMeasurementAttribute:
        return DatabaseMeasurementAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseCodeAttribute(DatabaseAttribute[CodeAttribute, Code]):
    """An attribute defined by a tag and a code value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Code | None] = mapped_column(code_db_type)
    updated_value: Mapped[Code | None] = mapped_column(code_db_type)
    mapped_value: Mapped[Code | None] = mapped_column(code_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Code | None = None,
        updated_value: Code | None = None,
        mapped_value: Code | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new code attribute.

        Parameters
        ----------
        schema: CodeAttributeSchema
            The schema of the attribute.
        value: Code | None = None
            The value of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.CODE,
    }
    __tablename__ = "code_attribute"

    @property
    def value(self) -> Code | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

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

    def copy(self) -> DatabaseCodeAttribute:
        return DatabaseCodeAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseBooleanAttribute(DatabaseAttribute[BooleanAttribute, bool]):
    """An attribute defined by a tag and a boolean value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[bool | None] = mapped_column(Boolean)
    updated_value: Mapped[bool | None] = mapped_column(Boolean)
    mapped_value: Mapped[bool | None] = mapped_column(Boolean)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: bool | None = None,
        updated_value: bool | None = None,
        mapped_value: bool | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new boolean attribute.

        Parameters
        ----------
        schema: BooleanAttributeSchema
            The schema of the attribute.
        value: bool | None = None
            The value of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.BOOLEAN,
    }
    __tablename__ = "boolean_attribute"

    @property
    def value(self) -> bool | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

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

    def copy(self) -> DatabaseBooleanAttribute:
        return DatabaseBooleanAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseObjectAttribute(
    DatabaseAttribute[ObjectAttribute, dict[str, AnyAttribute]]
):
    """An attribute that can have nested attributes."""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[dict[str, AnyAttribute] | None] = mapped_column(
        attribute_dict_db_type
    )
    updated_value: Mapped[dict[str, AnyAttribute] | None] = mapped_column(
        attribute_dict_db_type
    )
    mapped_value: Mapped[dict[str, AnyAttribute] | None] = mapped_column(
        attribute_dict_db_type
    )

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Mapping[str, AnyAttribute] | None = None,
        updated_value: Mapping[str, AnyAttribute] | None = None,
        mapped_value: Mapping[str, AnyAttribute] | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new object attribute.

        Parameters
        ----------
        schema: ObjectAttributeSchema
            The schema of the attribute.
        value: Sequence[AnyAttribute] | dict[str, AnyAttribute] | None = None
            The value (attributes) of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            display_value=display_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.OBJECT,
    }
    __tablename__ = "object_attribute"

    @property
    def value(self) -> dict[str, AnyAttribute] | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

    @property
    def model(self) -> ObjectAttribute:
        return ObjectAttribute(
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

    def copy(self) -> DatabaseObjectAttribute:
        return DatabaseObjectAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseListAttribute(DatabaseAttribute[ListAttribute, list[AnyAttribute]]):
    """Attribute that can hold a list of the same type (defined by schema)."""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[list[AnyAttribute] | None] = mapped_column(
        attribute_list_db_type
    )
    updated_value: Mapped[list[AnyAttribute] | None] = mapped_column(
        attribute_list_db_type
    )
    mapped_value: Mapped[list[AnyAttribute] | None] = mapped_column(
        attribute_list_db_type
    )

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Iterable[AnyAttribute] | None = None,
        updated_value: Iterable[AnyAttribute] | None = None,
        mapped_value: Iterable[AnyAttribute] | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new list attribute.

        Parameters
        ----------
        schema: ListAttributeSchema
            The schema of the attribute.
        value: list[AnyAttribute] | None = None
            The value (attributes) of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=list(original_value) if original_value is not None else None,
            updated_value=list(updated_value) if updated_value is not None else None,
            mapped_value=list(mapped_value) if mapped_value is not None else None,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.LIST,
    }
    __tablename__ = "attribute_list"

    @property
    def value(self) -> list[AnyAttribute] | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

    @property
    def model(self) -> ListAttribute:
        return ListAttribute(
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

    def copy(self) -> DatabaseListAttribute:
        return DatabaseListAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseUnionAttribute(DatabaseAttribute[UnionAttribute, AnyAttribute]):
    """Attribute that can be of different specified (by schema) type."""

    __allow_unmapped__ = True
    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    updated_value: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)
    mapped_value: Mapped[AnyAttribute | None] = mapped_column(attribute_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: AnyAttribute | None = None,
        updated_value: AnyAttribute | None = None,
        mapped_value: AnyAttribute | None = None,
        valid: bool = False,
        mappable_value: str | None = None,
        display_value: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a new union attribute.

        Parameters
        ----------
        schema: UnionAttributeSchema
            The schema of the attribute.
        value: AnyAttribute[Any, Any] | None = None
            The value (attribute) of the attribute, by default None.
        mappable_value: str | None = None
            The mappable value of the attribute, by default None.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            valid=valid,
            mappable_value=mappable_value,
            display_value=display_value,
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.UNION,
    }
    __tablename__ = "attribute_union"

    @property
    def value(self) -> AnyAttribute | None:
        """Return the effective value of the attribute."""
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
        return self.original_value

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

    def copy(self) -> DatabaseUnionAttribute:
        return DatabaseUnionAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )
