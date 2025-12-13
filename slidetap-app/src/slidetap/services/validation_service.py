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

from typing import Dict, Iterable, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseBatch,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.model import (
    AnyAttributeSchema,
    Attribute,
    Batch,
    BatchValidation,
    Dataset,
    DatasetValidation,
    Item,
    Project,
    ProjectValidation,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validators.attribute_validator import AttributeValidator
from slidetap.services.validators.relation_valiator import RelationValidator


class ValidationService:
    def __init__(
        self,
        schema_service: SchemaService,
        database_service: DatabaseService,
    ):
        self._schema_service = schema_service
        self._database_service = database_service
        self._attribute_validator = AttributeValidator()
        self._relation_validator = RelationValidator(schema_service, database_service)

    def validate_item(self, item: Union[UUID, Item, DatabaseItem], session: Session):
        item = self._database_service.get_item(session, item)
        self._validate_item_attributes(item)
        return self._relation_validator.validate_item_relations(item, session)

    def validate_item_relations(
        self, item: Union[UUID, Item, DatabaseItem], session: Session
    ):
        item = self._database_service.get_item(session, item)
        return self._relation_validator.validate_item_relations(item, session)

    def validate_item_attributes(
        self, item: Union[UUID, Item, DatabaseItem], session: Session
    ) -> Optional[bool]:
        item = self._database_service.get_item(session, item)
        return self._validate_item_attributes(item)

    def validate_project_attributes(
        self,
        project: Union[UUID, Project, DatabaseProject],
        session: Session,
    ) -> Optional[bool]:
        project = self._database_service.get_project(session, project)
        return self._validate_project_attributes(project)

    def validate_dataset_attributes(
        self,
        dataset: Union[UUID, Dataset, DatabaseDataset],
        session: Session,
    ) -> Optional[bool]:
        dataset = self._database_service.get_dataset(session, dataset)
        return self._validate_dataset_attributes(dataset)

    def validate_attribute(
        self,
        attribute: Union[Attribute, DatabaseAttribute, UUID],
        session: Session,
    ) -> bool:
        attribute = self._database_service.get_attribute(session, attribute)
        attribute_schema = self._schema_service.get_attribute(attribute.schema_uid)
        return self._attribute_validator.validate_attribute(attribute, attribute_schema)

    def get_validation_for_project(
        self,
        project: Union[UUID, Project, DatabaseProject],
    ) -> ProjectValidation:
        with self._database_service.get_session() as session:
            project = self._database_service.get_project(session, project)
            return self._get_validation_for_project(project)

    def get_validation_for_dataset(
        self,
        dataset: Union[UUID, Dataset, DatabaseDataset],
        session: Session,
    ) -> DatasetValidation:
        with self._database_service.get_session() as session:
            dataset = self._database_service.get_dataset(session, dataset)
            return self._get_validation_for_dataset(dataset)

    def get_validation_for_batch(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
    ) -> BatchValidation:
        with self._database_service.get_session() as session:
            batch = self._database_service.get_batch(session, batch)
            return self._get_validation_for_batch(batch, session)

    def _validate_item_attributes(self, item: DatabaseItem) -> Optional[bool]:
        schema = self._schema_service.items[item.schema_uid]
        item.valid_attributes = all(
            self._validate_database_attributes(item.attributes, schema.attributes)
        )
        return item.valid_attributes

    def _validate_project_attributes(self, project: DatabaseProject) -> Optional[bool]:
        schema = self._schema_service.root.project
        project.valid_attributes = all(
            self._validate_database_attributes(project.attributes, schema.attributes)
        )
        return project.valid_attributes

    def _validate_dataset_attributes(self, dataset: DatabaseDataset) -> Optional[bool]:
        schema = self._schema_service.root.dataset
        dataset.valid_attributes = all(
            self._validate_database_attributes(dataset.attributes, schema.attributes)
        )
        return dataset.valid_attributes

    def _validate_database_attributes(
        self,
        attributes: Iterable[DatabaseAttribute],
        schemas: Dict[str, AnyAttributeSchema],
    ) -> Iterable[bool]:
        results: Dict[str, bool] = {
            attribute.tag: self._attribute_validator.validate_attribute(
                attribute, schemas[attribute.tag]
            )
            for attribute in attributes
        }
        unhandled_tags = set(schemas.keys()) - set(results.keys())
        for tag in unhandled_tags:
            results[tag] = schemas[tag].optional
        return results.values()

    def _get_validation_for_project(
        self, project: DatabaseProject
    ) -> ProjectValidation:
        non_valid_attributes = [
            attribute.tag for attribute in project.attributes if not attribute.valid
        ]
        return ProjectValidation(
            valid=len(non_valid_attributes) == 0,
            uid=project.uid,
            non_valid_attributes=non_valid_attributes,
        )

    def _get_validation_for_dataset(
        self, dataset: DatabaseDataset
    ) -> DatasetValidation:
        non_valid_attributes = [
            attribute.tag for attribute in dataset.attributes if not attribute.valid
        ]

        return DatasetValidation(
            valid=len(non_valid_attributes) == 0,
            uid=dataset.uid,
            non_valid_attributes=non_valid_attributes,
        )

    def _get_validation_for_batch(
        self, batch: DatabaseBatch, session: Session
    ) -> BatchValidation:
        schemas = self._schema_service.items.values()
        items = (
            item
            for schema in schemas
            for item in self._database_service.get_items(session, schema, batch=batch)
        )
        non_valid_items = [item.uid for item in items if not item.valid]

        return BatchValidation(
            valid=len(non_valid_items) == 0,
            uid=batch.uid,
            non_valid_items=non_valid_items,
        )
