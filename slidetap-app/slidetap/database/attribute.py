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
from datetime import datetime
from typing import (
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
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
from sqlalchemy.ext.hybrid import hybrid_property
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
    tag: Mapped[str] = mapped_column(String(128), index=True)
    mappable_value: Mapped[Optional[str]] = mapped_column(String(512))
    valid: Mapped[bool] = mapped_column(Boolean, default=False)
    display_value: Mapped[Optional[str]] = mapped_column(String(512))
    attribute_value_type: Mapped[AttributeValueType] = mapped_column(
        Enum(AttributeValueType), index=True
    )
    schema_uid: Mapped[UUID] = mapped_column(Uuid)
    read_only: Mapped[bool] = mapped_column(Boolean, default=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)

    # For relations
    item_uid: Mapped[Optional[UUID]] = mapped_column(ForeignKey("item.uid"), index=True)
    project_uid: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("project.uid"), index=True
    )
    dataset_uid: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("dataset.uid"), index=True
    )
    mapping_item_uid: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("mapping_item.uid"), index=True
    )
    __table_args__ = (
        UniqueConstraint(
            "schema_uid", "item_uid", "project_uid", "dataset_uid", "mapping_item_uid"
        ),
    )

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        mappable_value: Optional[str] = None,
        read_only: bool = False,
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

            Whether to commit the attribute to the database, by default False.
        """
        super().__init__(
            tag=tag,
            schema_uid=schema_uid,
            mappable_value=mappable_value,
            read_only=read_only,
            uid=uid if (uid != UUID(int=0) and uid) else uuid4(),
            **kwargs,
        )
        self.display_value = self._set_display_value()

    __mapper_args__ = {
        "polymorphic_on": "attribute_value_type",
    }
    __tablename__ = "attribute"

    @hybrid_property
    def value(self) -> ValueStorageType:
        if self.updated_value is not None:
            return self.updated_value
        if self.mapped_value is not None:
            return self.mapped_value
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

    def set_mapping(
        self,
        value: ValueStorageType,
    ) -> None:
        """Set the mapping of the attribute.

        Parameters
        ----------
        mapping: MappingItem
            The mapping to set.
        """
        self._raise_if_not_editable()
        logging.debug("Setting mapping for attribute {self.uid} to {value}")
        self.mapped_value = value
        self.display_value = self._set_display_value()

    def clear_mapping(
        self,
    ):
        """Clear the mapping of the attribute."""
        self._raise_if_not_editable()
        self.mapped_value = None

    def set_value(
        self,
        value: Optional[ValueStorageType],
    ) -> None:
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
        self.updated_value = value
        self.display_value = self._set_display_value()

    def set_mappable_value(self, value: Optional[str]) -> None:
        """Set the mappable value of the attribute.

        Parameters
        ----------
        value: Optional[str]
            The mappable value to set.
        """
        self._raise_if_not_editable()
        self.mappable_value = value

    def set_original_value(
        self,
        value: Optional[ValueStorageType],
    ):
        """Set the original value of the attribute.

        Parameters
        ----------
        value: Optional[ValueType]
            The value to set.
        """
        self._raise_if_not_editable()
        self.original_value = value
        self.display_value = self._set_display_value()

    @abstractmethod
    def copy(self) -> DatabaseAttribute:
        """Copy the attribute."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def model(self) -> Attribute:
        raise NotImplementedError()

    def _raise_if_not_editable(self):
        if self.read_only:
            raise NotAllowedActionError(f"Cannot edit read only attribute {self.tag}.")
        if self.locked:
            raise NotAllowedActionError(f"Cannot edit locked attribute {self.tag}.")


class DatabaseStringAttribute(DatabaseAttribute[StringAttribute, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[str]] = mapped_column(String(512))
    updated_value: Mapped[Optional[str]] = mapped_column(String(512))
    mapped_value: Mapped[Optional[str]] = mapped_column(String(512))

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[str] = None,
        updated_value: Optional[str] = None,
        mapped_value: Optional[str] = None,
        mappable_value: Optional[str] = None,
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
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseEnumAttribute(DatabaseAttribute[EnumAttribute, str]):
    """An attribute defined by a tag and a string value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[str]] = mapped_column(String(128))
    updated_value: Mapped[Optional[str]] = mapped_column(String(128))
    mapped_value: Mapped[Optional[str]] = mapped_column(String(128))

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[str] = None,
        updated_value: Optional[str] = None,
        mapped_value: Optional[str] = None,
        mappable_value: Optional[str] = None,
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
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseDatetimeAttribute(DatabaseAttribute[DatetimeAttribute, datetime]):
    """An attribute defined by a tag and a datetime value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_value: Mapped[Optional[datetime]] = mapped_column(DateTime)
    mapped_value: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[datetime] = None,
        updated_value: Optional[datetime] = None,
        mapped_value: Optional[datetime] = None,
        mappable_value: Optional[str] = None,
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
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseNumericAttribute(DatabaseAttribute[NumericAttribute, float]):
    """An attribute defined by a tag and a float value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[float]] = mapped_column(Float)
    updated_value: Mapped[Optional[float]] = mapped_column(Float)
    mapped_value: Mapped[Optional[float]] = mapped_column(Float)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[float] = None,
        updated_value: Optional[float] = None,
        mapped_value: Optional[float] = None,
        mappable_value: Optional[str] = None,
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
    original_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)
    updated_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)
    mapped_value: Mapped[Optional[Measurement]] = mapped_column(measurement_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[Measurement] = None,
        updated_value: Optional[Measurement] = None,
        mapped_value: Optional[Measurement] = None,
        mappable_value: Optional[str] = None,
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
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseCodeAttribute(DatabaseAttribute[CodeAttribute, Code]):
    """An attribute defined by a tag and a code value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Code]] = mapped_column(code_db_type)
    updated_value: Mapped[Optional[Code]] = mapped_column(code_db_type)
    mapped_value: Mapped[Optional[Code]] = mapped_column(code_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[Code] = None,
        updated_value: Optional[Code] = None,
        mapped_value: Optional[Code] = None,
        mappable_value: Optional[str] = None,
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
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseBooleanAttribute(DatabaseAttribute[BooleanAttribute, bool]):
    """An attribute defined by a tag and a boolean value"""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Optional[bool]]] = mapped_column(Boolean)
    updated_value: Mapped[Optional[Optional[bool]]] = mapped_column(Boolean)
    mapped_value: Mapped[Optional[Optional[bool]]] = mapped_column(Boolean)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[bool] = None,
        updated_value: Optional[bool] = None,
        mapped_value: Optional[bool] = None,
        mappable_value: Optional[str] = None,
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
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseObjectAttribute(DatabaseAttribute[ObjectAttribute, Dict[str, Attribute]]):
    """An attribute that can have nested attributes."""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Dict[str, Attribute]]] = mapped_column(
        attribute_dict_db_type
    )
    updated_value: Mapped[Optional[Dict[str, Attribute]]] = mapped_column(
        attribute_dict_db_type
    )
    mapped_value: Mapped[Optional[Dict[str, Attribute]]] = mapped_column(
        attribute_dict_db_type
    )
    display_value_format_string: Mapped[Optional[str]] = mapped_column(String(512))

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[Mapping[str, Attribute]] = None,
        updated_value: Optional[Mapping[str, Attribute]] = None,
        mapped_value: Optional[Mapping[str, Attribute]] = None,
        mappable_value: Optional[str] = None,
        display_value_format_string: Optional[str] = None,
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
            original_value=original_value,
            updated_value=updated_value,
            mapped_value=mapped_value,
            display_value_format_string=display_value_format_string,
            uid=uid,
        )

    __mapper_args__ = {
        "polymorphic_identity": AttributeValueType.OBJECT,
    }
    __tablename__ = "object_attribute"

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
                logging.error(
                    f"Failed to format string {format_string} with attributes "
                    f"{self.value.keys()}",
                    exc_info=True,
                )
        if self.mappable_value is not None:
            return self.mappable_value
        return f"{self.tag}[{len(self.value or [])}]"

    def copy(self) -> DatabaseObjectAttribute:
        return DatabaseObjectAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
            display_value_format_string=self.display_value_format_string,
        )


class DatabaseListAttribute(DatabaseAttribute[ListAttribute, List[Attribute]]):
    """Attribute that can hold a list of the same type (defined by schema)."""

    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
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
        original_value: Optional[Iterable[Attribute]] = None,
        updated_value: Optional[Iterable[Attribute]] = None,
        mapped_value: Optional[Iterable[Attribute]] = None,
        mappable_value: Optional[str] = None,
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

    def copy(self) -> DatabaseListAttribute:
        return DatabaseListAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )


class DatabaseUnionAttribute(DatabaseAttribute[UnionAttribute, Attribute]):
    """Attribute that can be of different specified (by schema) type."""

    __allow_unmapped__ = True
    uid: Mapped[UUID] = mapped_column(ForeignKey("attribute.uid"), primary_key=True)
    original_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)
    updated_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)
    mapped_value: Mapped[Optional[Attribute]] = mapped_column(attribute_db_type)

    def __init__(
        self,
        tag: str,
        schema_uid: UUID,
        original_value: Optional[Attribute] = None,
        updated_value: Optional[Attribute] = None,
        mapped_value: Optional[Attribute] = None,
        mappable_value: Optional[str] = None,
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
            return self.mapped_value
        return self.original_value

    def copy(self) -> DatabaseUnionAttribute:
        return DatabaseUnionAttribute(
            tag=self.tag,
            schema_uid=self.schema_uid,
            original_value=self.original_value,
            updated_value=self.updated_value,
            mapped_value=self.mapped_value,
            mappable_value=self.mappable_value,
        )
