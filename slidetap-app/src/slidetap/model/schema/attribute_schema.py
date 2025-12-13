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

"""Schema models for attributes."""

import datetime
from abc import ABCMeta, abstractmethod
from typing import (
    Annotated,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field
from slidetap.model.attribute import (
    AnyAttribute,
    AttributeType,
)
from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.code import Code
from slidetap.model.datetime_value import DatetimeType
from slidetap.model.measurement import Measurement

AttributeSchemaType = TypeVar("AttributeSchemaType", bound="AttributeSchema")


class AttributeSchema(FrozenBaseModel, Generic[AttributeType], metaclass=ABCMeta):
    """Base schema for all attribute types."""

    uid: UUID
    tag: str
    name: str
    display_name: str
    optional: bool
    read_only: bool
    display_in_table: bool
    description: Optional[str] = None

    @abstractmethod
    def create_display_value(self, value: AttributeType) -> str:
        """Set the display value based on the attribute type."""
        raise NotImplementedError("Subclasses must implement set_display_value method.")


class StringAttributeSchema(AttributeSchema[str]):
    """Schema for string attributes."""

    multiline: bool = False
    attribute_value_type: Literal[AttributeValueType.STRING] = AttributeValueType.STRING

    def create_display_value(self, value: str) -> str:
        return value


class EnumAttributeSchema(AttributeSchema[str]):
    """Schema for enumerated string attributes."""

    allowed_values: Tuple[str, ...]
    attribute_value_type: Literal[AttributeValueType.ENUM] = AttributeValueType.ENUM

    def create_display_value(self, value: str) -> str:
        return value


class DatetimeAttributeSchema(AttributeSchema[datetime.datetime]):
    """Schema for datetime attributes."""

    datetime_type: DatetimeType
    attribute_value_type: Literal[AttributeValueType.DATETIME] = (
        AttributeValueType.DATETIME
    )

    def create_display_value(self, value: datetime.datetime) -> str:
        return str(value)


class NumericAttributeSchema(AttributeSchema[Union[int, float]]):
    """Schema for numeric attributes."""

    is_integer: bool
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    attribute_value_type: Literal[AttributeValueType.NUMERIC] = (
        AttributeValueType.NUMERIC
    )

    def create_display_value(self, value: Union[int, float]) -> str:
        return str(value)


class MeasurementAttributeSchema(AttributeSchema[Measurement]):
    """Schema for measurement attributes with units."""

    allowed_units: Optional[Tuple[str, ...]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    attribute_value_type: Literal[AttributeValueType.MEASUREMENT] = (
        AttributeValueType.MEASUREMENT
    )

    def create_display_value(self, value: Measurement) -> str:
        return f"{value.value} {value.unit}"


class CodeAttributeSchema(AttributeSchema[Code]):
    """Schema for coded values with schemas."""

    allowed_schemas: Optional[Tuple[str, ...]] = None
    attribute_value_type: Literal[AttributeValueType.CODE] = AttributeValueType.CODE

    def create_display_value(self, value: Code) -> str:
        return value.meaning


class BooleanAttributeSchema(AttributeSchema[bool]):
    """Schema for boolean attributes with custom display values."""

    true_display_value: str
    false_display_value: str
    attribute_value_type: Literal[AttributeValueType.BOOLEAN] = (
        AttributeValueType.BOOLEAN
    )

    def create_display_value(self, value: bool) -> str:
        return self.true_display_value if value else self.false_display_value


class ObjectAttributeSchema(AttributeSchema[Dict[str, AnyAttribute]]):
    """Schema for nested object attributes."""

    display_attributes_in_parent: bool
    display_value_tags: Sequence[str] = Field(exclude=True)
    display_value_tags_joiner: str = Field(default=", ", exclude=True)
    attributes: Dict[
        str,
        Annotated[
            Union[
                StringAttributeSchema,
                EnumAttributeSchema,
                DatetimeAttributeSchema,
                NumericAttributeSchema,
                MeasurementAttributeSchema,
                CodeAttributeSchema,
                BooleanAttributeSchema,
                "ObjectAttributeSchema",
                "ListAttributeSchema",
                "UnionAttributeSchema",
            ],
            Field(discriminator="attribute_value_type"),
        ],
    ]
    attribute_value_type: Literal[AttributeValueType.OBJECT] = AttributeValueType.OBJECT

    def create_display_value(
        self,
        value: Dict[str, AnyAttribute],
    ) -> str:
        values = [value.get(tag, None) for tag in self.display_value_tags]
        formated_values = [
            value.display_value
            for value in values
            if value is not None and value.display_value is not None
        ]
        return self.display_value_tags_joiner.join(formated_values)


class ListAttributeSchema(AttributeSchema[List[AnyAttribute]]):
    """Schema for list attributes."""

    display_attributes_in_parent: bool
    attribute: Annotated[
        Union[
            StringAttributeSchema,
            EnumAttributeSchema,
            DatetimeAttributeSchema,
            NumericAttributeSchema,
            MeasurementAttributeSchema,
            CodeAttributeSchema,
            BooleanAttributeSchema,
            ObjectAttributeSchema,
            "ListAttributeSchema",
            "UnionAttributeSchema",
        ],
        Field(discriminator="attribute_value_type"),
    ]
    attribute_value_type: Literal[AttributeValueType.LIST] = AttributeValueType.LIST

    def create_display_value(self, value: List[AnyAttribute]) -> str:
        if len(value) == 0:
            return "[]"
        display_values = [
            (attribute.display_value if attribute.display_value is not None else "N/A")
            for attribute in value
        ]
        return f"[{', '.join(display_values)}]"


class UnionAttributeSchema(AttributeSchema[AnyAttribute]):
    """Schema for union attributes that can be one of multiple types."""

    attributes: Tuple[
        Annotated[
            Union[
                StringAttributeSchema,
                EnumAttributeSchema,
                DatetimeAttributeSchema,
                NumericAttributeSchema,
                MeasurementAttributeSchema,
                CodeAttributeSchema,
                BooleanAttributeSchema,
                ObjectAttributeSchema,
                ListAttributeSchema,
                "UnionAttributeSchema",
            ],
            Field(discriminator="attribute_value_type"),
        ],
        ...,
    ]
    attribute_value_type: Literal[AttributeValueType.UNION] = AttributeValueType.UNION

    def create_display_value(self, value: AnyAttribute) -> str:
        attribute_schema = next(
            schema for schema in self.attributes if schema.uid == value.schema_uid
        )
        return attribute_schema.create_display_value(value.value)  # type: ignore


AnyAttributeSchema = Annotated[
    Union[
        StringAttributeSchema,
        EnumAttributeSchema,
        DatetimeAttributeSchema,
        NumericAttributeSchema,
        MeasurementAttributeSchema,
        CodeAttributeSchema,
        BooleanAttributeSchema,
        ObjectAttributeSchema,
        ListAttributeSchema,
        UnionAttributeSchema,
    ],
    Field(discriminator="attribute_value_type"),
]
