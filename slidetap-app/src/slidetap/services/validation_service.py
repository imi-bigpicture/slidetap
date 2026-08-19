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

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
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
    MetadataImportCompleteness,
    Project,
    ProjectValidation,
)
from slidetap.model.validation import NonValidItem
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validators.attribute_validator import AttributeValidator
from slidetap.services.validators.relation_validator import RelationValidator


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

    def validate_item(self, item: UUID | Item | DatabaseItem, session: Session):
        item = self._database_service.get_item(session, item)
        self._validate_item_attributes(item)
        self._validate_item_pseudonym(item)
        return self._relation_validator.validate_item_relations(item, session)

    def validate_item_relations(
        self,
        item: UUID | Item | DatabaseItem,
        session: Session,
        visited: set[UUID] | None = None,
    ):
        item = self._database_service.get_item(session, item)
        return self._relation_validator.validate_item_relations(
            item, session, visited=visited
        )

    def validate_relations_for(
        self, items: Iterable[UUID | Item | DatabaseItem], session: Session
    ) -> None:
        """Validate relations across a group of items that are all in their
        final state.

        Validating an item validates the other side of each of its relations
        too, so validating them one by one revisits the same neighbours once
        per relation that leads to them — quadratic in the size of the group,
        and each visit writes ``valid_relations`` again. Here one pass is
        shared, so every item the group reaches, whether it is in the group or
        an older item related to one, is validated exactly once.

        Only for items that are done being written. Anything validated while
        the rest of its relations are still arriving keeps the answer it had
        at the time.
        """
        visited: set[UUID] = set()
        for item in items:
            self.validate_item_relations(item, session, visited=visited)

    def item_is_as_complete_as_expected(
        self,
        item: DatabaseItem,
        completeness: MetadataImportCompleteness,
        session: Session,
    ) -> bool:
        """Whether an item is as valid as it is expected to be at this point in
        the batch's life.

        Parameters
        ----------
        item: DatabaseItem
            The item to judge.
        completeness: MetadataImportCompleteness
            What the import does not include, and so is not counted against
            the item. An empty one holds it to plain validity.
        session: Session
            Session to count the item's relations in.

        Returns
        -------
        bool
            Whether every part of validity holds, less what is excluded.

            Not stored on the item: this excuses what the import has not
            supplied yet and holds only until it has, while ``valid`` excludes
            nothing and is what the rest of the application reads. Storing it
            would leave an item that was excused looking valid once the excuse
            no longer applied.
        """
        if item.valid:
            # Nothing to excuse it of, and the stored answer already accounts
            # for everything, including whatever else `valid` covers.
            return True
        # One part per term of `valid`, so that excusing one leaves the others
        # answering for themselves.
        attributes_are_valid = (
            item.schema_uid in completeness.non_complete_items
            or bool(item.valid_attributes)
        )
        relations_are_valid = self._relation_validator.relations_are_valid(
            item, session, completeness.non_complete_relations
        )
        pseudonym_is_valid = bool(item.valid_pseudonym)
        not_failed = not (isinstance(item, DatabaseImage) and item.failed)
        return (
            attributes_are_valid
            and relations_are_valid
            and pseudonym_is_valid
            and not_failed
        )

    def validate_item_attributes(
        self, item: UUID | Item | DatabaseItem, session: Session
    ) -> bool | None:
        item = self._database_service.get_item(session, item)
        return self._validate_item_attributes(item)

    def validate_item_pseudonym(
        self, item: UUID | Item | DatabaseItem, session: Session
    ) -> bool:
        item = self._database_service.get_item(session, item)
        return self._validate_item_pseudonym(item)

    def validate_project_attributes(
        self,
        project: UUID | Project | DatabaseProject,
        session: Session,
    ) -> bool | None:
        project = self._database_service.get_project(session, project)
        return self._validate_project_attributes(project)

    def validate_dataset_attributes(
        self,
        dataset: UUID | Dataset | DatabaseDataset,
        session: Session,
    ) -> bool | None:
        dataset = self._database_service.get_dataset(session, dataset)
        return self._validate_dataset_attributes(dataset)

    def validate_attribute(
        self,
        attribute: Attribute | DatabaseAttribute | UUID,
        session: Session,
    ) -> bool:
        attribute = self._database_service.get_attribute(session, attribute)
        attribute_schema = self._schema_service.get_attribute(attribute.schema_uid)
        return self._attribute_validator.validate_attribute(attribute, attribute_schema)

    def get_validation_for_project(
        self,
        project: UUID | Project | DatabaseProject,
    ) -> ProjectValidation:
        with self._database_service.get_session() as session:
            project = self._database_service.get_project(session, project)
            return self._get_validation_for_project(project)

    def get_validation_for_dataset(
        self,
        dataset: UUID | Dataset | DatabaseDataset,
        session: Session,
    ) -> DatasetValidation:
        with self._database_service.get_session() as session:
            dataset = self._database_service.get_dataset(session, dataset)
            return self._get_validation_for_dataset(dataset)

    def get_validation_for_batch(
        self,
        batch: UUID | Batch | DatabaseBatch,
    ) -> BatchValidation:
        with self._database_service.get_session() as session:
            batch = self._database_service.get_batch(session, batch)
            return self._get_validation_for_batch(batch, session)

    def _validate_item_attributes(self, item: DatabaseItem) -> bool | None:
        schema = self._schema_service.items[item.schema_uid]
        item.valid_attributes = all(
            self._validate_database_attributes(item.attributes, schema.attributes)
        )
        return item.valid_attributes

    def _validate_item_pseudonym(self, item: DatabaseItem) -> bool:
        schema = self._schema_service.items[item.schema_uid]
        if schema.pseudonym_required and not item.pseudonym:
            item.valid_pseudonym = False
        else:
            item.valid_pseudonym = True
        return item.valid_pseudonym

    def _validate_project_attributes(self, project: DatabaseProject) -> bool | None:
        schema = self._schema_service.root.project
        project.valid_attributes = all(
            self._validate_database_attributes(project.attributes, schema.attributes)
        )
        return project.valid_attributes

    def _validate_dataset_attributes(self, dataset: DatabaseDataset) -> bool | None:
        schema = self._schema_service.root.dataset
        dataset.valid_attributes = all(
            self._validate_database_attributes(dataset.attributes, schema.attributes)
        )
        return dataset.valid_attributes

    def _validate_database_attributes(
        self,
        attributes: Iterable[DatabaseAttribute],
        schemas: dict[str, AnyAttributeSchema],
    ) -> Iterable[bool]:
        results: dict[str, bool] = {
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
            for item in self._database_service.get_items(
                session, schema, batch=batch, selected=True
            )
        )
        non_valid_items = [
            NonValidItem(
                uid=item.uid, identifier=item.identifier, schema_uid=item.schema_uid
            )
            for item in items
            if not item.valid
        ]

        return BatchValidation(
            valid=len(non_valid_items) == 0,
            uid=batch.uid,
            non_valid_items=non_valid_items,
        )
