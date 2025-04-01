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

from slidetap.database import DatabaseDataset, DatabaseItem, DatabaseProject
from slidetap.database.attribute import DatabaseAttribute
from slidetap.model import (
    Attribute,
    Item,
)
from slidetap.model.dataset import Dataset
from slidetap.model.project import Project
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService
from sqlalchemy import select
from sqlalchemy.orm import Session


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

    def update(self, attribute: Attribute, commit: bool = True) -> Attribute:
        with self._database_service.get_session() as session:
            existing_attribute = self._database_service.get_attribute(
                session, attribute.uid
            )
            if existing_attribute is None:
                raise ValueError(f"Attribute with uid {attribute.uid} does not exist")
            existing_attribute.set_value(attribute.updated_value)
            existing_attribute.set_mappable_value(attribute.mappable_value)
            self._validation_service.validate_attribute(existing_attribute, session)
            if existing_attribute.item_uid is not None:
                self._validation_service.validate_item_attributes(
                    existing_attribute.item_uid, session
                )
            elif existing_attribute.project_uid is not None:
                self._validation_service.validate_dataset_attributes(
                    existing_attribute.project_uid, session
                )
            elif existing_attribute.dataset_uid is not None:
                self._validation_service.validate_dataset_attributes(
                    existing_attribute.dataset_uid, session
                )
            if commit:
                session.commit()

            return existing_attribute.model

    def update_for_item(
        self,
        item: Union[UUID, Item, DatabaseItem],
        attributes: Dict[str, Attribute],
        commit: bool = True,
        session: Optional[Session] = None,
    ) -> Dict[str, Attribute]:
        updated_attributes: Dict[str, Attribute] = {}
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_item(session, item)
            for tag, attribute in attributes.items():
                database_attribute = session.scalars(
                    select(DatabaseAttribute).filter_by(item_uid=item.uid, tag=tag)
                ).one_or_none()
                if database_attribute is None:
                    database_attribute = self._database_service.add_attribute(
                        session,
                        attribute,
                        self._schema_service.get_attribute(attribute.schema_uid),
                        commit=False,
                    )
                    item.attributes[tag] = database_attribute
                else:
                    database_attribute.set_value(attribute.updated_value)
                    database_attribute.set_mappable_value(attribute.mappable_value)
                self._validation_service.validate_attribute(database_attribute, session)
                updated_attributes[tag] = database_attribute.model
            self._validation_service.validate_item_attributes(item.uid, session)
            if commit:
                session.commit()
        return updated_attributes

    def update_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
        attributes: Dict[str, Attribute],
        commit: bool = True,
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
            if commit:
                session.commit()
        return updated_attributes

    def update_for_dataset(
        self,
        dataset: Union[UUID, Dataset, DatabaseDataset],
        attributes: Dict[str, Attribute],
        commit: bool = True,
    ) -> Dict[str, Attribute]:
        updated_attributes: Dict[str, Attribute] = {}
        with self._database_service.get_session() as session:
            dataset = self._database_service.get_dataset(session, dataset)
            for tag, attribute in attributes.items():
                existing_attribute = session.scalars(
                    select(DatabaseAttribute).filter_by(
                        dataset_uid=dataset.uid, tag=tag
                    )
                ).one()
                existing_attribute.set_value(attribute.updated_value)
                existing_attribute.set_mappable_value(attribute.mappable_value)
                self._validation_service.validate_attribute(existing_attribute, session)
                updated_attributes[tag] = existing_attribute.model
            self._validation_service.validate_dataset_attributes(dataset, session)
            if commit:
                session.commit()
        return updated_attributes

    def create(
        self,
        attribute: Attribute,
        commit: bool = True,
    ) -> Attribute:
        with self._database_service.get_session() as session:
            created_attribute = self._database_service.add_attribute(
                session,
                attribute,
                self._schema_service.get_attribute(attribute.schema_uid),
                commit=False,
            )
            self._validation_service.validate_attribute(created_attribute, session)
            if created_attribute.item_uid is not None:
                self._validation_service.validate_item_attributes(
                    created_attribute.item_uid, session
                )
            elif created_attribute.project_uid is not None:
                self._validation_service.validate_project_attributes(
                    created_attribute.project_uid, session
                )
            elif created_attribute.dataset_uid is not None:
                self._validation_service.validate_dataset_attributes(
                    created_attribute.dataset_uid, session
                )
            if commit:
                session.commit()
            return created_attribute.model

    def create_for_item(
        self,
        item: Union[UUID, Item, DatabaseItem],
        attributes: Dict[str, Attribute],
        commit: bool = True,
        session: Optional[Session] = None,
    ) -> Dict[str, Attribute]:
        created_attributes: Dict[str, Attribute] = {}
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_item(session, item)
            for tag, attribute in attributes.items():
                created_attribute = self._database_service.add_attribute(
                    session,
                    attribute,
                    self._schema_service.get_attribute(attribute.schema_uid),
                    commit=False,
                )
                item.attributes[tag] = created_attribute
                created_attributes[tag] = created_attribute.model
            if commit:
                session.commit()
        return created_attributes

    def create_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
        attributes: Dict[str, Attribute],
        commit: bool = True,
        session: Optional[Session] = None,
    ) -> Dict[str, Attribute]:
        created_attributes: Dict[str, Attribute] = {}
        with self._database_service.get_session() as session:
            project = self._database_service.get_project(session, project)
            for tag, attribute in attributes.items():
                created_attribute = self._database_service.add_attribute(
                    session,
                    attribute,
                    self._schema_service.get_attribute(attribute.schema_uid),
                    commit=False,
                )
                project.attributes[tag] = created_attribute
                self._validation_service.validate_attribute(created_attribute, session)
                created_attributes[tag] = created_attribute.model
            self._validation_service.validate_project_attributes(project.uid, session)
            if commit:
                session.commit()
        return created_attributes

    def create_for_dataset(
        self,
        dataset: Union[UUID, Dataset, DatabaseDataset],
        attributes: Dict[str, Attribute],
        commit: bool = True,
    ) -> Dict[str, Attribute]:
        created_attributes: Dict[str, Attribute] = {}
        with self._database_service.get_session() as session:
            dataset = self._database_service.get_dataset(session, dataset)
            for tag, attribute in attributes.items():
                created_attribute = self._database_service.add_attribute(
                    session,
                    attribute,
                    self._schema_service.get_attribute(attribute.schema_uid),
                    commit=False,
                )
                dataset.attributes[tag] = created_attribute
                self._validation_service.validate_attribute(created_attribute, session)
                created_attributes[tag] = created_attribute.model
            self._validation_service.validate_dataset_attributes(dataset, session)
            if commit:
                session.commit()
        return created_attributes
