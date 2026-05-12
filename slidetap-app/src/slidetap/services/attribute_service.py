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

import logging
from typing import Dict, Iterable, List, Optional, Union, overload
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.database.attribute import DatabaseObjectAttribute
from slidetap.model import (
    AnyAttribute,
    Attribute,
    AttributeSchema,
    BooleanAttribute,
    BooleanAttributeSchema,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
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
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get(self, attribute_uid: UUID) -> Optional[AnyAttribute]:
        with self._database_service.get_session() as session:
            attribute = self._database_service.get_attribute(session, attribute_uid)
            if attribute is None:
                return None
            return attribute.model

    def get_for_schema(self, attribute_schema_uid: UUID) -> Iterable[AnyAttribute]:
        with self._database_service.get_session() as session:
            attributes = self._database_service.get_attributes_for_schema(
                session, attribute_schema_uid
            )
            return [attribute.model for attribute in attributes]

    def update(
        self,
        attribute: Attribute,
        validate: bool = True,
        session: Optional[Session] = None,
    ) -> AnyAttribute:
        with self._database_service.get_session(session) as session:
            existing_attribute = self._database_service.get_attribute(
                session, attribute.uid
            )
            if existing_attribute is None:
                raise ValueError(f"Attribute with uid {attribute.uid} does not exist")
            self.set_display_value(attribute)
            existing_attribute.set_value(
                attribute.updated_value, attribute.display_value
            )
            existing_attribute.set_mapping_item_uid(attribute.mapping_item_uid)
            existing_attribute.set_mapped_value(attribute.mapped_value)
            existing_attribute.set_mappable_value(attribute.mappable_value)
            if validate:
                self._validation_service.validate_attribute(existing_attribute, session)
                if existing_attribute.attribute_item_uid is not None:
                    self._validation_service.validate_item_attributes(
                        existing_attribute.attribute_item_uid, session
                    )
                elif existing_attribute.attribute_project_uid is not None:
                    self._validation_service.validate_project_attributes(
                        existing_attribute.attribute_project_uid, session
                    )
                elif existing_attribute.attribute_dataset_uid is not None:
                    self._validation_service.validate_dataset_attributes(
                        existing_attribute.attribute_dataset_uid, session
                    )
            return existing_attribute.model

    def update_for_item(
        self,
        item: Union[UUID, Item, DatabaseItem],
        attributes: Iterable[AnyAttribute],
        session: Optional[Session] = None,
    ) -> None:
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_item(session, item)
            for attribute in attributes:
                self.set_display_value(attribute)
                database_attribute = self._database_service.get_optional_attribute(
                    session, attribute.uid
                )
                if database_attribute is None:
                    database_attribute = self._database_service.add_attribute(
                        session,
                        attribute,
                        self._schema_service.get_attribute(attribute.schema_uid),
                    )
                    item.attributes.add(database_attribute)
                else:
                    database_attribute.set_value(
                        attribute.updated_value, attribute.display_value
                    )
                    database_attribute.set_mappable_value(attribute.mappable_value)
                self._validation_service.validate_attribute(database_attribute, session)
            self._validation_service.validate_item_attributes(item.uid, session)

    def update_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
        attributes: Iterable[AnyAttribute],
    ) -> None:
        with self._database_service.get_session() as session:
            project = self._database_service.get_project(session, project)
            for attribute in attributes:
                self.set_display_value(attribute)
                database_attribute = self._database_service.get_attribute(
                    session, attribute.uid
                )
                database_attribute.set_value(
                    attribute.updated_value, attribute.display_value
                )
                database_attribute.set_mappable_value(attribute.mappable_value)
                self._validation_service.validate_attribute(database_attribute, session)
            self._validation_service.validate_project_attributes(project.uid, session)

    def update_for_dataset(
        self,
        dataset: Union[UUID, Dataset, DatabaseDataset],
        attributes: Iterable[AnyAttribute],
    ) -> None:
        with self._database_service.get_session() as session:
            dataset = self._database_service.get_dataset(session, dataset)
            for attribute in attributes:
                self.set_display_value(attribute)

                database_attribute = self._database_service.get_attribute(
                    session, attribute.uid
                )
                database_attribute.set_value(
                    attribute.updated_value, attribute.display_value
                )
                database_attribute.set_mappable_value(attribute.mappable_value)
                self._validation_service.validate_attribute(database_attribute, session)
            self._validation_service.validate_dataset_attributes(dataset, session)

    def create(
        self,
        attribute: Attribute,
    ) -> AnyAttribute:
        with self._database_service.get_session() as session:
            created_attribute = self._database_service.add_attribute(
                session,
                attribute,
                self._schema_service.get_attribute(attribute.schema_uid),
            )
            self._validation_service.validate_attribute(created_attribute, session)
            if created_attribute.attribute_item_uid is not None:
                self._validation_service.validate_item_attributes(
                    created_attribute.attribute_item_uid, session
                )
            elif created_attribute.attribute_project_uid is not None:
                self._validation_service.validate_project_attributes(
                    created_attribute.attribute_project_uid, session
                )
            elif created_attribute.attribute_dataset_uid is not None:
                self._validation_service.validate_dataset_attributes(
                    created_attribute.attribute_dataset_uid, session
                )
            return created_attribute.model

    def create_or_update_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        session: Optional[Session] = None,
    ) -> List[DatabaseAttribute]:
        with self._database_service.get_session(session) as session:
            return self._create_or_update_attributes(attributes, session)

    def create_or_update_private_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        session: Optional[Session] = None,
    ) -> List[DatabaseAttribute]:
        with self._database_service.get_session(session) as session:
            return self._create_or_update_private_attributes(attributes, session)

    def _create_or_update_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        session: Session,
    ) -> List[DatabaseAttribute]:
        database_attributes: List[DatabaseAttribute] = []
        for attribute in attributes:
            self.set_display_value(attribute)
            database_attribute = self._database_service.get_optional_attribute(
                session, attribute
            )
            if database_attribute:
                database_attribute.set_value(attribute.value, attribute.display_value)
            else:
                database_attribute = self._database_service.add_attribute(
                    session,
                    attribute,
                    self._schema_service.get_attribute(attribute.schema_uid),
                )

            database_attributes.append(database_attribute)
        return database_attributes

    def _create_or_update_private_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        session: Session,
    ) -> List[DatabaseAttribute]:
        database_attributes: List[DatabaseAttribute] = []
        for attribute in attributes:
            self.set_display_value(attribute)
            database_attribute = self._database_service.get_optional_attribute(
                session, attribute
            )

            if database_attribute:
                database_attribute.set_value(attribute.value, attribute.display_value)
            else:
                database_attribute = self._database_service.add_attribute(
                    session,
                    attribute,
                    self._schema_service.get_private_attribute(attribute.schema_uid),
                )
            database_attributes.append(database_attribute)
        return database_attributes

    def set_display_value(self, attribute: Attribute) -> None:
        """Set ``attribute.display_value`` from its schema's renderer.

        Public so callers in other services (e.g. ``MapperService``) can
        compute the same display string instead of duplicating the logic.
        """
        schema = self._schema_service.get_any_attribute(attribute.schema_uid)
        if attribute.value is None:
            attribute.display_value = None
        else:
            attribute.display_value = schema.create_display_value(attribute.value)

    @staticmethod
    def resolve_attribute(
        attributes: Dict[str, AnyAttribute],
        tag: str,
    ) -> Optional[AnyAttribute]:
        """Resolve a possibly nested attribute tag from a Pydantic
        attribute dict. Supports compound ``parent.child`` tags by walking
        into the parent ObjectAttribute's effective value (updated > mapped
        > original).
        """
        if tag in attributes:
            return attributes[tag]
        parent_tag, _, child_tag = tag.partition(".")
        if not child_tag:
            return None
        parent_attr = attributes.get(parent_tag)
        if not isinstance(parent_attr, ObjectAttribute):
            return None
        for value_dict in (
            parent_attr.updated_value,
            parent_attr.mapped_value,
            parent_attr.original_value,
        ):
            if value_dict and child_tag in value_dict:
                return value_dict[child_tag]
        return None

    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: StringAttributeSchema,
    ) -> StringAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: EnumAttributeSchema,
    ) -> EnumAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: DatetimeAttributeSchema,
    ) -> DatetimeAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: NumericAttributeSchema,
    ) -> NumericAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: MeasurementAttributeSchema,
    ) -> MeasurementAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: CodeAttributeSchema,
    ) -> CodeAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: BooleanAttributeSchema,
    ) -> BooleanAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: ObjectAttributeSchema,
    ) -> ObjectAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: ListAttributeSchema,
    ) -> ListAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: UnionAttributeSchema,
    ) -> UnionAttribute: ...
    @staticmethod
    def empty_attribute_from_schema(schema: AttributeSchema) -> AnyAttribute:
        """Construct an empty attribute matching ``schema``.

        Used when creating new items so the schema-defined attribute
        structure exists immediately. Without this, freshly-created items
        have no attributes at all and editors that reach into nested
        ObjectAttributes (e.g. ``statement.diagnose``) have nothing to
        merge into.

        Children of ObjectAttributes are not pre-materialised — clients
        render placeholders for missing children from the schema and the
        deep-merge on save fills them in.
        """
        base = {
            "uid": uuid4(),
            "schema_uid": schema.uid,
            "valid": schema.optional,
        }
        if isinstance(schema, StringAttributeSchema):
            return StringAttribute(**base)
        if isinstance(schema, EnumAttributeSchema):
            return EnumAttribute(**base)
        if isinstance(schema, DatetimeAttributeSchema):
            return DatetimeAttribute(**base)
        if isinstance(schema, NumericAttributeSchema):
            return NumericAttribute(**base)
        if isinstance(schema, MeasurementAttributeSchema):
            return MeasurementAttribute(**base)
        if isinstance(schema, CodeAttributeSchema):
            return CodeAttribute(**base)
        if isinstance(schema, BooleanAttributeSchema):
            return BooleanAttribute(**base)
        if isinstance(schema, ObjectAttributeSchema):
            return ObjectAttribute(**base)
        if isinstance(schema, ListAttributeSchema):
            return ListAttribute(**base)
        if isinstance(schema, UnionAttributeSchema):
            return UnionAttribute(**base)
        raise TypeError(f"Unknown attribute schema type {type(schema).__name__}.")

    def swap_attribute_value(
        self,
        source: DatabaseItem,
        target: DatabaseItem,
        attribute_tag: str,
    ) -> None:
        """Exchange the value at ``attribute_tag`` between two items.

        For a top-level tag, exchanges the user/mapped fields. For a compound
        ``parent.child`` tag, exchanges the child slot inside each side's
        parent ObjectAttribute and recomputes the parent's ``display_value``
        so table renderers stay in sync.
        """
        parent_tag, _, child_tag = attribute_tag.partition(".")

        source_attr = self._find_top_level_attribute(source, parent_tag)
        target_attr = self._find_top_level_attribute(target, parent_tag)
        if source_attr is None or target_attr is None:
            raise ValueError(
                f"Attribute '{parent_tag}' missing on source or target"
            )

        if not child_tag:
            # original_value is the import-time source-of-truth and stays put.
            source_attr.updated_value, target_attr.updated_value = (
                target_attr.updated_value,
                source_attr.updated_value,
            )
            source_attr.mapped_value, target_attr.mapped_value = (
                target_attr.mapped_value,
                source_attr.mapped_value,
            )
            source_attr.mappable_value, target_attr.mappable_value = (
                target_attr.mappable_value,
                source_attr.mappable_value,
            )
            source_attr.display_value, target_attr.display_value = (
                target_attr.display_value,
                source_attr.display_value,
            )
            return

        if not isinstance(source_attr, DatabaseObjectAttribute) or not isinstance(
            target_attr, DatabaseObjectAttribute
        ):
            raise ValueError(
                f"Compound tag '{attribute_tag}' requires '{parent_tag}' to be "
                f"an object attribute on both sides"
            )
        source_child = self._read_object_child(source_attr, child_tag)
        target_child = self._read_object_child(target_attr, child_tag)
        self._write_object_child(source_attr, child_tag, target_child)
        self._write_object_child(target_attr, child_tag, source_child)
        self._refresh_object_display_value(source_attr)
        self._refresh_object_display_value(target_attr)

    def _refresh_object_display_value(
        self, parent: DatabaseObjectAttribute
    ) -> None:
        """Recompute and store the parent ObjectAttribute's ``display_value``
        from its effective value. Table cells render from ``display_value``
        directly, so leaving it stale after a child-swap blanks the column.
        """
        schema = self._schema_service.get_any_attribute(parent.schema_uid)
        value = parent.value
        if value is None or not value:
            parent.display_value = None
        else:
            parent.display_value = schema.create_display_value(value)

    @staticmethod
    def _find_top_level_attribute(
        item: DatabaseItem, tag: str
    ) -> Optional[DatabaseAttribute]:
        for attr in (*item.attributes, *item.private_attributes):
            if attr.tag == tag:
                return attr
        return None

    @staticmethod
    def _read_object_child(
        parent: DatabaseObjectAttribute, child_tag: str
    ) -> Optional[AnyAttribute]:
        for value_dict in (
            parent.updated_value,
            parent.mapped_value,
            parent.original_value,
        ):
            if value_dict and child_tag in value_dict:
                return value_dict[child_tag]
        return None

    @classmethod
    def _write_object_child(
        cls,
        parent: DatabaseObjectAttribute,
        child_tag: str,
        child_value: Optional[AnyAttribute],
    ) -> None:
        base = (
            parent.updated_value
            or parent.mapped_value
            or parent.original_value
            or {}
        )
        new_value = dict(base)
        if child_value is None or cls._is_attribute_model_empty(child_value):
            new_value.pop(child_tag, None)
        else:
            new_value[child_tag] = child_value
        parent.updated_value = new_value

    @staticmethod
    def _is_attribute_model_empty(attr: AnyAttribute) -> bool:
        return (
            attr.updated_value is None
            and attr.mapped_value is None
            and attr.original_value is None
        )
