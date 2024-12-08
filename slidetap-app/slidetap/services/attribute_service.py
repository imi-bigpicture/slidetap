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

"""Service for accessing attributes."""

from typing import Dict, Iterable, Optional, Tuple, Union
from uuid import UUID

from slidetap.database import (
    DatabaseAttribute,
    DatabaseBooleanAttribute,
    DatabaseBooleanAttributeSchema,
    DatabaseCodeAttribute,
    DatabaseCodeAttributeSchema,
    DatabaseItem,
    DatabaseListAttribute,
    DatabaseListAttributeSchema,
    DatabaseMeasurementAttribute,
    DatabaseMeasurementAttributeSchema,
    DatabaseNumericAttribute,
    DatabaseNumericAttributeSchema,
    DatabaseObjectAttribute,
    DatabaseObjectAttributeSchema,
    DatabaseProject,
    DatabaseStringAttribute,
    DatabaseStringAttributeSchema,
    DatabaseUnionAttribute,
    DatabaseUnionAttributeSchema,
)
from slidetap.database.schema.attribute_schema import DatabaseAttributeSchema
from slidetap.model.attribute import (
    Attribute,
    BooleanAttribute,
    CodeAttribute,
    ListAttribute,
    MeasurementAttribute,
    NumericAttribute,
    ObjectAttribute,
    StringAttribute,
    UnionAttribute,
)
from slidetap.model.item import Item
from slidetap.model.project import Project
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class AttributeService:
    """Attribute service should be used to interface with attributes"""

    def __init__(
        self, schema_service: SchemaService, validation_service: ValidationService
    ):
        self._schema_service = schema_service
        self._validation_service = validation_service

    def get(self, attribute_uid: UUID) -> Optional[Attribute]:
        attribute = DatabaseAttribute.get(attribute_uid)
        if attribute is None:
            return None
        return attribute.model

    def get_for_schema(self, attribute_schema_uid: UUID) -> Iterable[Attribute]:
        return (
            attribute.model
            for attribute in DatabaseAttribute.get_for_attribute_schema(
                attribute_schema_uid
            )
        )

    def update(self, attribute: Attribute) -> Attribute:
        existing_attribute = DatabaseAttribute.get(attribute.uid)
        if existing_attribute is None:
            raise ValueError(f"Attribute with uid {attribute.uid} does not exist")
        existing_attribute.set_value(attribute.updated_value)
        existing_attribute.set_mappable_value(attribute.mappable_value)
        self._validation_service.validate_attribute(existing_attribute)
        if existing_attribute.item_uid is not None:
            self._validation_service.validate_attributes_for_item(
                existing_attribute.item_uid
            )
        elif existing_attribute.project_uid is not None:
            self._validation_service.validate_attributes_for_project(
                existing_attribute.project_uid
            )
        return existing_attribute.model

    def update_for_item(
        self, item: Union[UUID, Item, DatabaseItem], attributes: Dict[str, Attribute]
    ) -> Dict[str, Attribute]:
        if isinstance(item, UUID):
            item = DatabaseItem.get(item)
        elif isinstance(item, Item):
            item = DatabaseItem.get(item.uid)
        updated_attributes: Dict[str, Attribute] = {}
        for tag, attribute in attributes.items():
            existing_attribute = item.attributes[tag]
            existing_attribute.set_value(attribute.updated_value)
            existing_attribute.set_mappable_value(attribute.mappable_value)
            self._validation_service.validate_attribute(existing_attribute)
            updated_attributes[tag] = existing_attribute.model
        self._validation_service.validate_attributes_for_item(item.uid)
        return updated_attributes

    def update_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
        attributes: Dict[str, Attribute],
    ) -> Dict[str, Attribute]:
        if isinstance(project, UUID):
            project = DatabaseProject.get(project)
        elif isinstance(project, Project):
            project = DatabaseProject.get(project.uid)
        updated_attributes: Dict[str, Attribute] = {}
        for tag, attribute in attributes.items():
            existing_attribute = project.attributes[tag]
            existing_attribute.set_value(attribute.updated_value)
            existing_attribute.set_mappable_value(attribute.mappable_value)
            self._validation_service.validate_attribute(existing_attribute)
            updated_attributes[tag] = existing_attribute.model
        self._validation_service.validate_attributes_for_project(project.uid)
        return updated_attributes

    def create(
        self,
        attribute: Attribute,
    ) -> Attribute:
        created_attribute = self._create(attribute)
        self._validation_service.validate_attribute(created_attribute)
        if created_attribute.item_uid is not None:
            self._validation_service.validate_attributes_for_item(
                created_attribute.item_uid
            )
        elif created_attribute.project_uid is not None:
            self._validation_service.validate_attributes_for_project(
                created_attribute.project_uid
            )
        return created_attribute.model

    def create_for_item(
        self, item: Union[UUID, Item, DatabaseItem], attributes: Dict[str, Attribute]
    ) -> Dict[str, Attribute]:
        if isinstance(item, UUID):
            item = DatabaseItem.get(item)
        elif isinstance(item, Item):
            item = DatabaseItem.get(item.uid)
        created_attributes: Dict[str, Attribute] = {}
        for tag, attribute in attributes.items():
            created_attribute = self._create(attribute)
            item.attributes[tag] = created_attribute
            self._validation_service.validate_attribute(created_attribute)
            created_attributes[tag] = created_attribute.model
        self._validation_service.validate_attributes_for_item(item.uid)
        return created_attributes

    def create_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
        attributes: Dict[str, Attribute],
    ) -> Dict[str, Attribute]:
        if isinstance(project, UUID):
            project = DatabaseProject.get(project)
        elif isinstance(project, Project):
            project = DatabaseProject.get(project.uid)
        created_attributes: Dict[str, Attribute] = {}
        for tag, attribute in attributes.items():
            created_attribute = self._create(attribute)
            project.attributes[tag] = created_attribute
            self._validation_service.validate_attribute(created_attribute)
            created_attributes[tag] = created_attribute.model
        self._validation_service.validate_attributes_for_project(project.uid)
        return created_attributes

    def _create(self, attribute: Attribute) -> DatabaseAttribute:
        attribute_schema = DatabaseAttributeSchema.get(attribute.schema_uid)
        if isinstance(attribute, StringAttribute) and isinstance(
            attribute_schema, DatabaseStringAttributeSchema
        ):
            return DatabaseStringAttribute(
                attribute_schema,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
            )
        if isinstance(attribute, NumericAttribute) and isinstance(
            attribute_schema, DatabaseNumericAttributeSchema
        ):
            return DatabaseNumericAttribute(
                attribute_schema,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
            )
        if isinstance(attribute, MeasurementAttribute) and isinstance(
            attribute_schema, DatabaseMeasurementAttributeSchema
        ):
            return DatabaseMeasurementAttribute(
                attribute_schema,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
            )
        if isinstance(attribute, CodeAttribute) and isinstance(
            attribute_schema, DatabaseCodeAttributeSchema
        ):
            return DatabaseCodeAttribute(
                attribute_schema,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
            )
        if isinstance(attribute, BooleanAttribute) and isinstance(
            attribute_schema, DatabaseBooleanAttributeSchema
        ):
            return DatabaseBooleanAttribute(
                attribute_schema,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
            )
        if isinstance(attribute, ObjectAttribute) and isinstance(
            attribute_schema, DatabaseObjectAttributeSchema
        ):
            return DatabaseObjectAttribute(
                attribute_schema,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
            )
        if isinstance(attribute, ListAttribute) and isinstance(
            attribute_schema, DatabaseListAttributeSchema
        ):
            return DatabaseListAttribute(
                attribute_schema,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
            )
        if isinstance(attribute, UnionAttribute) and isinstance(
            attribute_schema, DatabaseUnionAttributeSchema
        ):
            return DatabaseUnionAttribute(
                attribute_schema,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
            )
        raise NotImplementedError(f"Non-implemented create for {attribute_schema}")
