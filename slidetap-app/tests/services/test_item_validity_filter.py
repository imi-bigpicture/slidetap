#    Copyright 2026 SECTRA AB
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

"""Tests that a table can ask the database which rows are waiting on the import.

A table filters, sorts and counts over the whole dataset rather than over the
page it is showing, so the difference between a row that is waiting and a row
that is wrong has to be one the database can answer. It is: whether the schema
is one the import leaves short is settled once for the query, and the rest is
the columns validity is already stored in.
"""

from uuid import UUID, uuid4

import pytest
from decoy import Decoy

from slidetap.model import (
    BatchStatus,
    Dataset,
    ImageFormat,
    ImageStatus,
    ItemValidity,
    MetadataImportCompleteness,
    Project,
    RootSchema,
)
from slidetap.model.batch import BatchCreate
from slidetap.model.item import Image
from slidetap.model.schema.item_schema import ImageSchema
from slidetap.model.schema.review_layout import ReviewLayout
from slidetap.model.schema.review_unit_schema import ReviewUnitSchema
from slidetap.model.table import ColumnSort, SortType
from slidetap.services import DatabaseService, SchemaService
from slidetap.services.validation_service import ValidationService

# One image per answer the column can give, told apart by what is wrong with
# it: nothing, only what the import has not read out of the file yet, and
# something no import is going to settle.
IMAGES = {
    "valid": {"attributes": True, "relations": True, "status": ImageStatus.NOT_STARTED},
    "pending": {
        "attributes": False,
        "relations": True,
        "status": ImageStatus.NOT_STARTED,
    },
    "parked": {
        "attributes": False,
        "relations": False,
        "status": ImageStatus.NOT_STARTED,
    },
    "failed": {
        "attributes": False,
        "relations": True,
        "status": ImageStatus.DOWNLOADING_FAILED,
    },
}


@pytest.fixture()
def image_schema(schema: RootSchema) -> ImageSchema:
    return next(iter(schema.images.values()))


@pytest.fixture()
def review_unit(image_schema: ImageSchema) -> ReviewUnitSchema:
    """An application whose import brings images in before their files are
    read, which is where the images' attributes come from."""
    return ReviewUnitSchema(
        schema_uid=uuid4(),
        layout=ReviewLayout(uid=uuid4(), name="review"),
        completeness=MetadataImportCompleteness(
            non_complete_items=frozenset({image_schema.uid})
        ),
    )


@pytest.fixture()
def validation_service(
    decoy: Decoy,
    sqlite_database_service: DatabaseService,
    review_unit: ReviewUnitSchema,
) -> ValidationService:
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.review_unit).then_return(review_unit)
    return ValidationService(
        schema_service=schema_service, database_service=sqlite_database_service
    )


def add_images(
    database_service: DatabaseService,
    image_schema: ImageSchema,
    dataset: Dataset,
    project: Project,
    batch_status: BatchStatus,
) -> dict[str, UUID]:
    """An image per entry in `IMAGES`, in one batch that has got as far as
    `batch_status`.

    Written onto the rows rather than validated into being: what is under test
    is the reading, and validating would bring the whole graph into it.
    """
    uids: dict[str, UUID] = {}
    with database_service.get_session() as session:
        database_service.add_dataset(session, dataset)
        database_service.add_project(session, project)
        batch = database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        )
        batch.status = batch_status
        for identifier, wanted in IMAGES.items():
            image = Image(
                uid=uuid4(),
                identifier=identifier,
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=image_schema.uid,
                format=ImageFormat.DICOM_WSI,
            )
            database_image = database_service.add_item(session, image, [], [])
            database_image.valid_attributes = bool(wanted["attributes"])
            database_image.valid_relations = bool(wanted["relations"])
            database_image.valid_pseudonym = True
            database_image.status = wanted["status"]
            uids[identifier] = database_image.uid
    return uids


@pytest.mark.integration
class TestAskingTheDatabaseWhichRowsAreWaiting:
    @pytest.mark.parametrize(
        ("validity", "expected"),
        [
            (ItemValidity.VALID, {"valid"}),
            (ItemValidity.PENDING, {"pending"}),
            (ItemValidity.INVALID, {"parked", "failed"}),
        ],
    )
    def test_each_answer_holds_what_it_says(
        self,
        sqlite_database_service: DatabaseService,
        validation_service: ValidationService,
        image_schema: ImageSchema,
        dataset: Dataset,
        project: Project,
        validity: ItemValidity,
        expected: set[str],
    ):
        """The parked image is the one this is for: it is short of the same
        attributes as the pending one and of the slide it should hang under as
        well, and only a curator moving it settles that. The failed one is
        short of what nothing is going to bring any more."""
        # Arrange
        add_images(
            sqlite_database_service,
            image_schema,
            dataset,
            project,
            BatchStatus.METADATA_SEARCH_COMPLETE,
        )
        pending_expression = validation_service.pending_expression(image_schema)

        # Act
        with sqlite_database_service.get_session() as session:
            images = sqlite_database_service.get_images(
                session,
                image_schema,
                validity=validity,
                pending_expression=pending_expression,
            )
            identifiers = {image.identifier for image in images}
            count = sqlite_database_service.get_item_count(
                session,
                image_schema,
                validity=validity,
                pending_expression=pending_expression,
            )

        # Assert
        assert identifiers == expected
        assert count == len(expected)

    def test_the_answer_changes_when_the_images_are_in(
        self,
        sqlite_database_service: DatabaseService,
        validation_service: ValidationService,
        image_schema: ImageSchema,
        dataset: Dataset,
        project: Project,
    ):
        """Nothing on the rows changed: the batch did. What was waiting on the
        import is an image that came in without what it needs."""
        # Arrange
        add_images(
            sqlite_database_service,
            image_schema,
            dataset,
            project,
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
        )
        pending_expression = validation_service.pending_expression(image_schema)

        # Act
        with sqlite_database_service.get_session() as session:
            pending = sqlite_database_service.get_images(
                session,
                image_schema,
                validity=ItemValidity.PENDING,
                pending_expression=pending_expression,
            )
            invalid = sqlite_database_service.get_images(
                session,
                image_schema,
                validity=ItemValidity.INVALID,
                pending_expression=pending_expression,
            )

            # Assert
            assert {image.identifier for image in pending} == set()
            assert {image.identifier for image in invalid} == {
                "pending",
                "parked",
                "failed",
            }

    def test_an_application_that_excuses_nothing_asks_as_it_always_did(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        review_unit: ReviewUnitSchema,
        image_schema: ImageSchema,
        dataset: Dataset,
        project: Project,
    ):
        """No row can be waiting on anything, so nothing answers to pending and
        every row that is not valid is one to see to."""
        # Arrange
        schema_service = decoy.mock(cls=SchemaService)
        decoy.when(schema_service.review_unit).then_return(
            review_unit.model_copy(update={"completeness": None})
        )
        validation_service = ValidationService(
            schema_service=schema_service, database_service=sqlite_database_service
        )
        add_images(
            sqlite_database_service,
            image_schema,
            dataset,
            project,
            BatchStatus.METADATA_SEARCH_COMPLETE,
        )
        pending_expression = validation_service.pending_expression(image_schema)

        # Act
        with sqlite_database_service.get_session() as session:
            pending = sqlite_database_service.get_images(
                session,
                image_schema,
                validity=ItemValidity.PENDING,
                pending_expression=pending_expression,
            )
            invalid = sqlite_database_service.get_images(
                session,
                image_schema,
                validity=ItemValidity.INVALID,
                pending_expression=pending_expression,
            )

            # Assert
            assert pending_expression is None
            assert {image.identifier for image in pending} == set()
            assert {image.identifier for image in invalid} == {
                "pending",
                "parked",
                "failed",
            }

    def test_the_column_sorts_in_the_order_a_curator_reads_it(
        self,
        sqlite_database_service: DatabaseService,
        validation_service: ValidationService,
        image_schema: ImageSchema,
        dataset: Dataset,
        project: Project,
    ):
        """What is theirs to see to first, then what is only waiting, then what
        is done. Ordered in the database, since a page is not the dataset."""
        # Arrange
        add_images(
            sqlite_database_service,
            image_schema,
            dataset,
            project,
            BatchStatus.METADATA_SEARCH_COMPLETE,
        )
        pending_expression = validation_service.pending_expression(image_schema)

        # Act
        with sqlite_database_service.get_session() as session:
            images = sqlite_database_service.get_images(
                session,
                image_schema,
                sorting=[ColumnSort(sort_type=SortType.VALID, descending=False)],
                pending_expression=pending_expression,
            )
            identifiers = [image.identifier for image in images]

        # Assert
        assert set(identifiers[:2]) == {"parked", "failed"}
        assert identifiers[2:] == ["pending", "valid"]
