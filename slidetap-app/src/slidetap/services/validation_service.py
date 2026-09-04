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

from sqlalchemy import ColumnElement, and_, select
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
    BatchStatus,
    BatchValidation,
    Dataset,
    DatasetValidation,
    ImageStatus,
    Item,
    MetadataImportCompleteness,
    Project,
    ProjectValidation,
)
from slidetap.model.schema.item_schema import AnyItemSchema, ImageSchema
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

    def not_satisfied_relations(
        self, item: DatabaseItem, session: Session
    ) -> list[str]:
        """The relations an item does not satisfy, by name."""
        return self._relation_validator.not_satisfied_relations(item, session)

    def item_is_valid_for_now(
        self, item: UUID | Item | DatabaseItem, session: Session
    ) -> bool:
        """Whether an item is as valid as it is expected to be at this moment.

        Plain validity where the review unit says the import leaves nothing
        out, and once the batch is far enough along for what it leaves out to
        have arrived. Until then what the import does not include is not held
        against the item: nothing can be done about a slide whose image has not
        been imported yet, and counting it as wrong would say only that the
        import is not finished.

        Read from the batch the item is in rather than from the one its review
        unit is in, since what has been imported is a fact about that batch. A
        sample whose children ended up in another batch is moved to the
        project's default batch, so the two are not always the same.
        """
        # Looked up only for what is not an item already, so that a caller
        # holding one is not made to pay for a query to hand it back.
        if isinstance(item, (UUID, Item)):
            item = self._database_service.get_item(session, item)
        if not item.selected:
            # Taken out of the project, and so holding nothing back: an item
            # that is going nowhere cannot be curated into being valid. What a
            # review unit answers for is read the same way.
            return True
        unit = self._schema_service.review_unit
        if (
            unit is None
            or unit.completeness is None
            or item.batch is None
            or item.batch.status >= BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        ):
            return item.valid
        return self.item_is_as_complete_as_expected(item, unit.completeness, session)

    def item_is_pending(self, item: DatabaseItem, session: Session) -> bool:
        """Whether the only thing an item is short of is what the import has
        not delivered yet.

        Not valid, and valid but for the attributes the review unit says are
        not in at this point in the batch's life. Asked where a row is drawn: a
        curator reading a case before its images have been fetched is told
        which rows are theirs to see to, and a row waiting on the import is not
        one of them.

        What is wrong for any other reason answers for itself. An image parked
        on the case fails the relation to the slide it should hang under, and
        no amount of waiting settles it -- only a curator moving it does -- so
        it is not pending, it is not valid.

        Only for an item still in the project: one taken out is not waiting for
        anything, which is how ``item_is_valid_for_now`` reads it too.
        """
        if item.valid or not item.selected:
            return False
        return self.item_is_valid_for_now(item, session)

    def pending_expression(self, schema: AnyItemSchema) -> ColumnElement[bool] | None:
        """The same question as ``item_is_pending``, asked of a query.

        The table sorts and filters in the database over the whole dataset
        rather than over the page it is showing, so the rule has to be
        answerable there too. It is, without reading anything the rows do not
        already hold: whether the schema is one the import leaves short is
        settled once, and the rest is the columns validity is stored in.

        ``None`` where no row of this schema can be waiting on anything --- the
        application excuses nothing, or excuses some other schema --- which
        leaves every query about validity exactly as it was.

        A review unit that excuses a relation rather than attributes is not
        answered here: what is stored is one boolean over every relation an
        item has, so leaving one out cannot be read off a row. Such a row reads
        as not valid in the table, which is what it read as before any of this.
        """
        unit = self._schema_service.review_unit
        if unit is None or unit.completeness is None:
            return None
        if schema.uid not in unit.completeness.non_complete_items:
            return None
        # Enumerated rather than compared: the status column holds the name of
        # the status, so `<` in the database would order them alphabetically
        # and put a metadata-search-complete batch on the wrong side of the
        # threshold.
        early = [
            status
            for status in BatchStatus
            if status < BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        ]
        terms: list[ColumnElement[bool]] = [
            DatabaseItem.valid_attributes.is_(False),
            DatabaseItem.valid_relations,
            DatabaseItem.valid_pseudonym,
            # A semi-join rather than a join: the batch is read to place the
            # row on one side of the import, not to add anything to it, and
            # joining would put the row in the result once per batch matched.
            DatabaseItem.batch_uid.in_(
                select(DatabaseBatch.uid).where(DatabaseBatch.status.in_(early))
            ),
        ]
        if isinstance(schema, ImageSchema):
            # As `DatabaseImage.valid` counts it: an image whose download or
            # processing failed is not waiting for anything.
            terms.append(
                DatabaseImage.status.notin_(
                    [
                        ImageStatus.DOWNLOADING_FAILED,
                        ImageStatus.PRE_PROCESSING_FAILED,
                        ImageStatus.POST_PROCESSING_FAILED,
                    ]
                )
            )
        return and_(*terms)

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
