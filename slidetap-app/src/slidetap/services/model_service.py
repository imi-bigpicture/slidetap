#    Copyright 2025 SECTRA AB
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

"""Service for accessing attributes."""

from uuid import uuid4

from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    BooleanAttribute,
    CodeAttribute,
    DatetimeAttribute,
    EnumAttribute,
    ListAttribute,
    ListAttributeSchema,
    MeasurementAttribute,
    NumericAttribute,
    ObjectAttribute,
    StringAttribute,
    UnionAttribute,
)
from slidetap.model.external import (
    AttributeExternal,
    BooleanAttributeExternal,
    CodeAttributeExternal,
    DatetimeAttributeExternal,
    EnumAttributeExternal,
    ListAttributeExternal,
    MeasurementAttributeExternal,
    NumericAttributeExternal,
    ObjectAttributeExternal,
    StringAttributeExternal,
    UnionAttributeExternal,
)
from slidetap.services.schema_service import SchemaService


class ModelService:

    def __init__(self, schema_service: SchemaService):
        self._schema_service = schema_service

    def attribute_to_external_attribute(
        self, attribute: AnyAttribute
    ) -> AttributeExternal:
        if attribute.value is None:
            raise ValueError("Attribute value is None")
        if isinstance(attribute, StringAttribute):
            return StringAttributeExternal(
                value=attribute.value,
                display_value=attribute.display_value,
            )
        if isinstance(attribute, EnumAttribute):
            return EnumAttributeExternal(
                value=attribute.value,
                display_value=attribute.display_value,
            )
        if isinstance(attribute, BooleanAttribute):
            return BooleanAttributeExternal(
                value=attribute.value,
                display_value=attribute.display_value,
            )
        if isinstance(attribute, CodeAttribute):
            return CodeAttributeExternal(
                value=attribute.value,
                display_value=attribute.display_value,
            )
        if isinstance(attribute, DatetimeAttribute):
            return DatetimeAttributeExternal(
                value=attribute.value,
                display_value=attribute.display_value,
            )
        if isinstance(attribute, MeasurementAttribute):
            return MeasurementAttributeExternal(
                value=attribute.value,
                display_value=attribute.display_value,
            )
        if isinstance(attribute, NumericAttribute):
            return NumericAttributeExternal(
                value=attribute.value,
                display_value=attribute.display_value,
            )
        if isinstance(attribute, ListAttribute):
            return ListAttributeExternal(
                value=[
                    self.attribute_to_external_attribute(child)
                    for child in attribute.value
                ],  # type: ignore
                display_value=attribute.display_value,
            )
        if isinstance(attribute, ObjectAttribute):
            return ObjectAttributeExternal(
                value={
                    tag: self.attribute_to_external_attribute(child)
                    for tag, child in attribute.value.items()
                },  # type: ignore
                display_value=attribute.display_value,
            )
        if isinstance(attribute, UnionAttribute):
            # For union, we need to determine which schema to use based on the value
            child_attribute = attribute.value
            schema = self._schema_service.get_attribute(child_attribute.schema_uid)
            return UnionAttributeExternal(
                attribute_name=schema.name,
                value=self.attribute_to_external_attribute(child_attribute),  # type: ignore
                display_value=attribute.display_value,
            )
        raise ValueError(f"Unsupported attribute type: {type(attribute)}")

    def external_attribute_to_attribute(
        self,
        external: AttributeExternal,
        attribute_schema: AttributeSchema,
    ) -> AnyAttribute:
        if isinstance(external, StringAttributeExternal):
            return StringAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=external.value,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, EnumAttributeExternal):
            return EnumAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=external.value,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, BooleanAttributeExternal):
            return BooleanAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=external.value,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, CodeAttributeExternal):
            return CodeAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=external.value,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, DatetimeAttributeExternal):
            return DatetimeAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=external.value,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, MeasurementAttributeExternal):
            return MeasurementAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=external.value,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, NumericAttributeExternal):
            return NumericAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=external.value,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, ListAttributeExternal):
            if not isinstance(attribute_schema, ListAttributeSchema):
                raise ValueError(
                    "Attribute schema is not ListAttributeSchema for ListAttributeExternal"
                )
            child_attribute_schema = attribute_schema.attribute
            children = [
                self.external_attribute_to_attribute(child, child_attribute_schema)
                for child in external.value
            ]
            return ListAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=children,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, ObjectAttributeExternal):
            child_attributes = {}
            for tag, child_external in external.value.items():
                child_schema = self._schema_service.get_attribute_by_name(tag)
                child_attributes[tag] = self.external_attribute_to_attribute(
                    child_external, child_schema
                )
            return ObjectAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=child_attributes,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        if isinstance(external, UnionAttributeExternal):
            # For union, we need to determine which schema to use based on the value
            child_schema = self._schema_service.get_attribute_by_name(
                external.attribute_name
            )
            child_attribute = self.external_attribute_to_attribute(
                external.value, child_schema
            )
            return UnionAttribute(
                uid=uuid4(),
                schema_uid=attribute_schema.uid,
                original_value=child_attribute,
                updated_value=None,
                mapped_value=None,
                valid=True,
                display_value=external.display_value,
                mappable_value=None,
            )
        raise ValueError(f"Unsupported mapping item type: {type(external)}")
