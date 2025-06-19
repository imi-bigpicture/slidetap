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

from typing import Annotated, Dict, Iterable, Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.model import (
    Attribute,
    Dataset,
    Item,
    Project,
)
from slidetap.model.attribute import AnyAttribute
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
        with self._database_service.get_session() as session:
            attribute = self._database_service.get_attribute(session, attribute_uid)
            if attribute is None:
                return None
            return attribute.model

    def get_for_schema(self, attribute_schema_uid: UUID) -> Iterable[Attribute]:
        with self._database_service.get_session() as session:
            attributes = self._database_service.get_attributes_for_schema(
                session, attribute_schema_uid
            )
            return [attribute.model for attribute in attributes]

    def update(self, attribute: Attribute) -> Attribute:
        with self._database_service.get_session() as session:
            existing_attribute = self._database_service.get_attribute(
                session, attribute.uid
            )
            if existing_attribute is None:
                raise ValueError(f"Attribute with uid {attribute.uid} does not exist")
            existing_attribute.set_value(attribute.updated_value)
            existing_attribute.set_mappable_value(attribute.mappable_value)
            self._validation_service.validate_attribute(existing_attribute, session)
            if existing_attribute.attribute_item_uid is not None:
                self._validation_service.validate_item_attributes(
                    existing_attribute.attribute_item_uid, session
                )
            elif existing_attribute.attribute_project_uid is not None:
                self._validation_service.validate_dataset_attributes(
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
        attributes: Dict[str, AnyAttribute],
        session: Optional[Session] = None,
    ) -> Dict[str, AnyAttribute]:
        updated_attributes: Dict[str, AnyAttribute] = {}
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_item(session, item)
            for tag, attribute in attributes.items():
                database_attribute = session.scalars(
                    select(DatabaseAttribute).filter_by(
                        attribute_item_uid=item.uid, tag=tag
                    )
                ).one_or_none()
                if database_attribute is None:
                    database_attribute = self._database_service.add_attribute(
                        session,
                        attribute,
                        self._schema_service.get_attribute(attribute.schema_uid),
                    )
                    item.attributes[tag] = database_attribute
                else:
                    database_attribute.set_value(attribute.updated_value)
                    database_attribute.set_mappable_value(attribute.mappable_value)
                self._validation_service.validate_attribute(database_attribute, session)
                updated_attributes[tag] = database_attribute.model
            self._validation_service.validate_item_attributes(item.uid, session)
        return updated_attributes

    def update_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
        attributes: Dict[str, Attribute],
    ) -> Dict[str, Attribute]:
        updated_attributes: Dict[str, Attribute] = {}
        with self._database_service.get_session() as session:
            project = self._database_service.get_project(session, project)
            for tag, attribute in attributes.items():
                existing_attribute = session.scalars(
                    select(DatabaseAttribute).filter_by(
                        project_uid=project.uid, tag=tag
                    )
                ).one()
                existing_attribute.set_value(attribute.updated_value)
                existing_attribute.set_mappable_value(attribute.mappable_value)
                self._validation_service.validate_attribute(existing_attribute, session)
                updated_attributes[tag] = existing_attribute.model
            self._validation_service.validate_project_attributes(project.uid, session)
        return updated_attributes

    def update_for_dataset(
        self,
        dataset: Union[UUID, Dataset, DatabaseDataset],
        attributes: Dict[str, Attribute],
    ) -> Dict[str, Attribute]:
        updated_attributes: Dict[str, Attribute] = {}
        with self._database_service.get_session() as session:
            dataset = self._database_service.get_dataset(session, dataset)
            for tag, attribute in attributes.items():
                existing_attribute = session.scalars(
                    select(DatabaseAttribute).filter_by(
                        attribute_dataset_uid=dataset.uid, tag=tag
                    )
                ).one()
                existing_attribute.set_value(attribute.updated_value)
                existing_attribute.set_mappable_value(attribute.mappable_value)
                self._validation_service.validate_attribute(existing_attribute, session)
                updated_attributes[tag] = existing_attribute.model
            self._validation_service.validate_dataset_attributes(dataset, session)

        return updated_attributes

    def create(
        self,
        attribute: Attribute,
    ) -> Attribute:
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
        attributes: Dict[str, AnyAttribute],
        session: Optional[Session] = None,
    ) -> Dict[str, DatabaseAttribute]:
        with self._database_service.get_session(session) as session:
            return self._create_or_update_attributes(attributes, session)

    def create_or_update_private_attributes(
        self,
        attributes: Dict[str, AnyAttribute],
        session: Optional[Session] = None,
    ) -> Dict[str, DatabaseAttribute]:
        with self._database_service.get_session(session) as session:
            return self._create_or_update_attributes(attributes, session)

    def _create_or_update_attributes(
        self,
        attributes: Dict[str, AnyAttribute],
        session: Session,
    ) -> Dict[str, DatabaseAttribute]:
        database_attributes: Dict[str, DatabaseAttribute] = {}
        for tag, attribute in attributes.items():
            database_attribute = self._database_service.get_optional_attribute(
                session, attribute
            )
            if database_attribute:
                database_attribute.set_value(attribute.value)
            else:
                database_attribute = self._database_service.add_attribute(
                    session,
                    attribute,
                    self._schema_service.get_attribute(attribute.schema_uid),
                )

            database_attributes[tag] = database_attribute
        return database_attributes

    def _create_or_update_private_attributes(
        self,
        attributes: Dict[str, AnyAttribute],
        session: Session,
    ) -> Dict[str, DatabaseAttribute]:
        database_attributes: Dict[str, DatabaseAttribute] = {}
        for tag, attribute in attributes.items():
            database_attribute = self._database_service.get_optional_attribute(
                session, attribute
            )
            if database_attribute:
                database_attribute.set_value(attribute.value)
            else:
                database_attribute = self._database_service.add_attribute(
                    session,
                    attribute,
                    self._schema_service.get_private_attribute(attribute.schema_uid),
                )

            database_attributes[tag] = database_attribute
        return database_attributes
