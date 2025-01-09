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

from typing import Dict, Iterable, Optional, Union
from uuid import UUID

from slidetap.database import (
    DatabaseAttribute,
    DatabaseBooleanAttribute,
    DatabaseCodeAttribute,
    DatabaseDatetimeAttribute,
    DatabaseEnumAttribute,
    DatabaseItem,
    DatabaseListAttribute,
    DatabaseMeasurementAttribute,
    DatabaseNumericAttribute,
    DatabaseObjectAttribute,
    DatabaseProject,
    DatabaseStringAttribute,
    DatabaseUnionAttribute,
    db,
)
from slidetap.model import (
    Attribute,
    BooleanAttribute,
    BooleanAttributeSchema,
    CodeAttribute,
    CodeAttributeSchema,
    DatetimeAttribute,
    DatetimeAttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    Item,
    ListAttribute,
    ListAttributeSchema,
    MeasurementAttribute,
    MeasurementAttributeSchema,
    NumericAttribute,
    NumericAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    Project,
    StringAttribute,
    StringAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class AttributeService:
    """Attribute service should be used to interface with attributes"""

    def __init__(
        self,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
    ):
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service

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

    def update(self, attribute: Attribute, commit: bool = True) -> Attribute:
        existing_attribute = DatabaseAttribute.get(attribute.uid)
        if existing_attribute is None:
            raise ValueError(f"Attribute with uid {attribute.uid} does not exist")
        existing_attribute.set_value(attribute.updated_value, commit=commit)
        existing_attribute.set_mappable_value(attribute.mappable_value, commit=commit)
        self._validation_service.validate_attribute(existing_attribute)
        if existing_attribute.item_uid is not None:
            self._validation_service.validate_item_attributes(
                existing_attribute.item_uid
            )
        elif existing_attribute.project_uid is not None:
            self._validation_service.validate_project_attributes(
                existing_attribute.project_uid
            )
        return existing_attribute.model

    def update_for_item(
        self,
        item: Union[UUID, Item, DatabaseItem],
        attributes: Dict[str, Attribute],
        commit: bool = True,
    ) -> Dict[str, Attribute]:
        if isinstance(item, UUID):
            item = DatabaseItem.get(item)
        elif isinstance(item, Item):
            item = DatabaseItem.get(item.uid)
        updated_attributes: Dict[str, Attribute] = {}
        for tag, attribute in attributes.items():
            database_attribute = item.get_optional_attribute(tag)
            if database_attribute is None:
                database_attribute = self._create(attribute, False)
                item.attributes[tag] = database_attribute
            else:
                database_attribute.set_value(attribute.updated_value, commit=False)
                database_attribute.set_mappable_value(
                    attribute.mappable_value, commit=False
                )
            self._validation_service.validate_attribute(database_attribute)
            updated_attributes[tag] = database_attribute.model
        self._validation_service.validate_item_attributes(item.uid)
        if commit:
            db.session.commit()
        return updated_attributes

    def update_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
        attributes: Dict[str, Attribute],
        commit: bool = True,
    ) -> Dict[str, Attribute]:
        project = self._database_service.get_project(project)
        updated_attributes: Dict[str, Attribute] = {}
        for tag, attribute in attributes.items():
            existing_attribute = project.get_attribute(tag)
            existing_attribute.set_value(attribute.updated_value, commit=commit)
            existing_attribute.set_mappable_value(
                attribute.mappable_value, commit=commit
            )
            self._validation_service.validate_attribute(existing_attribute)
            updated_attributes[tag] = existing_attribute.model
        self._validation_service.validate_project_attributes(project.uid)
        return updated_attributes

    def create(
        self,
        attribute: Attribute,
        commit: bool = True,
    ) -> Attribute:
        created_attribute = self._create(attribute, commit)
        self._validation_service.validate_attribute(created_attribute)
        if created_attribute.item_uid is not None:
            self._validation_service.validate_item_attributes(
                created_attribute.item_uid
            )
        elif created_attribute.project_uid is not None:
            self._validation_service.validate_project_attributes(
                created_attribute.project_uid
            )
        return created_attribute.model

    def create_for_item(
        self,
        item: Union[UUID, Item, DatabaseItem],
        attributes: Dict[str, Attribute],
        commit: bool = True,
    ) -> Dict[str, Attribute]:
        if isinstance(item, UUID):
            item = DatabaseItem.get(item)
        elif isinstance(item, Item):
            item = DatabaseItem.get(item.uid)
        created_attributes: Dict[str, Attribute] = {}
        for tag, attribute in attributes.items():
            created_attribute = self._create(attribute, commit)
            item.attributes[tag] = created_attribute
            created_attributes[tag] = created_attribute.model
        return created_attributes

    def create_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
        attributes: Dict[str, Attribute],
        commit: bool = True,
    ) -> Dict[str, Attribute]:
        project = self._database_service.get_project(project)
        created_attributes: Dict[str, Attribute] = {}
        for tag, attribute in attributes.items():
            created_attribute = self._create(attribute, commit)
            project.attributes[tag] = created_attribute
            self._validation_service.validate_attribute(created_attribute)
            created_attributes[tag] = created_attribute.model
        self._validation_service.validate_project_attributes(project.uid)
        return created_attributes

    def _create(self, attribute: Attribute, commit: bool = True) -> DatabaseAttribute:
        attribute_schema = self._schema_service.get_attribute(attribute.schema_uid)
        if isinstance(attribute, StringAttribute) and isinstance(
            attribute_schema, StringAttributeSchema
        ):
            return DatabaseStringAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, EnumAttribute) and isinstance(
            attribute_schema, EnumAttributeSchema
        ):
            return DatabaseEnumAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, DatetimeAttribute) and isinstance(
            attribute_schema, DatetimeAttributeSchema
        ):
            return DatabaseDatetimeAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, NumericAttribute) and isinstance(
            attribute_schema, NumericAttributeSchema
        ):
            return DatabaseNumericAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, MeasurementAttribute) and isinstance(
            attribute_schema, MeasurementAttributeSchema
        ):
            return DatabaseMeasurementAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, CodeAttribute) and isinstance(
            attribute_schema, CodeAttributeSchema
        ):
            return DatabaseCodeAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, BooleanAttribute) and isinstance(
            attribute_schema, BooleanAttributeSchema
        ):
            return DatabaseBooleanAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, ObjectAttribute) and isinstance(
            attribute_schema, ObjectAttributeSchema
        ):
            return DatabaseObjectAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                dict(attribute.original_value) if attribute.original_value else None,
                dict(attribute.updated_value) if attribute.updated_value else None,
                dict(attribute.mapped_value) if attribute.mapped_value else None,
                mappable_value=attribute.mappable_value,
                display_value_format_string=attribute_schema.display_value_format_string,
                commit=commit,
            )
        if isinstance(attribute, ListAttribute) and isinstance(
            attribute_schema, ListAttributeSchema
        ):
            return DatabaseListAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, UnionAttribute) and isinstance(
            attribute_schema, UnionAttributeSchema
        ):
            return DatabaseUnionAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        raise NotImplementedError(f"Non-implemented create for {attribute_schema}")
