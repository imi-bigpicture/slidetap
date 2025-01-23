from typing import Dict, Iterable, Union
from uuid import UUID

from slidetap.database import (
    DatabaseAttribute,
    DatabaseBatch,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.model import (
    Attribute,
    AttributeSchema,
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
        self, schema_service: SchemaService, database_service: DatabaseService
    ):
        self._schema_service = schema_service
        self._database_service = database_service
        self._attribute_validator = AttributeValidator()
        self._relation_validator = RelationValidator(schema_service, database_service)

    def validate_item(self, item: Union[UUID, Item, DatabaseItem]):
        item = self._database_service.get_item(item)
        self._validate_item_attributes(item)
        self._relation_validator.validate_item_relations(item)

    def validate_item_relations(self, item: Union[UUID, Item, DatabaseItem]):
        item = self._database_service.get_item(item)
        self._relation_validator.validate_item_relations(item)

    def validate_item_attributes(self, item: Union[UUID, Item, DatabaseItem]):
        item = self._database_service.get_item(item)
        self._validate_item_attributes(item)

    def validate_project_attributes(
        self, project: Union[UUID, Project, DatabaseProject]
    ):
        project = self._database_service.get_project(project)
        self._validate_project_attributes(project)

    def validate_dataset_attributes(
        self, dataset: Union[UUID, Dataset, DatabaseDataset]
    ):
        dataset = self._database_service.get_dataset(dataset)
        self._validate_dataset_attributes(dataset)

    def validate_attribute(self, attribute: Union[Attribute, DatabaseAttribute, UUID]):
        attribute = self._database_service.get_attribute(attribute)
        attribute_schema = self._schema_service.get_attribute(attribute.schema_uid)
        self._attribute_validator.validate_attribute(attribute, attribute_schema)

    def get_validation_for_project(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> ProjectValidation:
        project = self._database_service.get_project(project)
        return self._get_validation_for_project(project)

    def get_validation_for_dataset(
        self, dataset: Union[UUID, Dataset, DatabaseDataset]
    ) -> DatasetValidation:
        dataset = self._database_service.get_dataset(dataset)
        return self._get_validation_for_dataset(dataset)

    def get_validation_for_batch(
        self, batch: Union[UUID, Batch, DatabaseBatch]
    ) -> BatchValidation:
        batch = self._database_service.get_batch(batch)
        return self._get_validation_for_batch(batch)

    def _validate_item_attributes(self, item: DatabaseItem):
        schema = self._schema_service.items[item.schema_uid]
        item.valid_attributes = all(
            self._validate_database_attributes(
                item.attributes.values(), schema.attributes
            )
        )

    def _validate_project_attributes(self, project: DatabaseProject):
        schema = self._schema_service.root.project
        project.valid_attributes = all(
            self._validate_database_attributes(
                project.attributes.values(), schema.attributes
            )
        )

    def _validate_dataset_attributes(self, dataset: DatabaseDataset):
        schema = self._schema_service.root.dataset
        dataset.valid_attributes = all(
            self._validate_database_attributes(
                dataset.attributes.values(), schema.attributes
            )
        )

    def _validate_database_attributes(
        self,
        attributes: Iterable[DatabaseAttribute],
        schemas: Dict[str, AttributeSchema],
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
            attribute.tag
            for attribute in project.attributes.values()
            if not attribute.valid
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
            attribute.tag
            for attribute in dataset.attributes.values()
            if not attribute.valid
        ]

        return DatasetValidation(
            valid=len(non_valid_attributes) == 0,
            uid=dataset.uid,
            non_valid_attributes=non_valid_attributes,
        )

    def _get_validation_for_batch(self, batch: DatabaseBatch) -> BatchValidation:
        items = self._database_service.get_items(batch=batch)
        non_valid_items = [item.uid for item in items if not item.valid]

        return BatchValidation(
            valid=len(non_valid_items) == 0,
            uid=batch.uid,
            non_valid_items=non_valid_items,
        )
