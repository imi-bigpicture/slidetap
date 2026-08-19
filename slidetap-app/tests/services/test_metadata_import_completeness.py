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

"""Tests for holding an item to what has arrived rather than to plain validity.

An importer fills a unit in over more than one pass, and the flagging that runs
when a unit is imported has to tell what is genuinely wrong with it from what
is merely still on its way. What is still on its way is named by the importer;
everything else is checked in earnest.
"""

from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from sqlalchemy.orm import Session

from slidetap.database import DatabaseBatch, DatabaseImage, DatabaseSample
from slidetap.model import BatchStatus, Cardinality, MetadataImportCompleteness
from slidetap.model.schema.item_relation import ImageToSampleRelation
from slidetap.model.schema.item_schema import ImageSchema, SampleSchema
from slidetap.model.schema.review_unit_schema import ReviewUnitSchema
from slidetap.services import DatabaseService, SchemaService
from slidetap.services.validation_service import ValidationService


@pytest.fixture()
def session(decoy: Decoy) -> Session:
    return decoy.mock(cls=Session)


@pytest.fixture()
def image_schema_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def slide_schema_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def slide_to_image(
    image_schema_uid: UUID, slide_schema_uid: UUID
) -> ImageToSampleRelation:
    """A slide is scanned at least once, and the image is of that one slide."""
    return ImageToSampleRelation(
        uid=uuid4(),
        name="Image of slide",
        description=None,
        image_uid=image_schema_uid,
        sample_uid=slide_schema_uid,
        images=Cardinality.ONE_OR_MORE,
        samples=Cardinality.ONE,
        image_title="WSI",
        sample_title="Slide",
    )


@pytest.fixture()
def image_schema(
    decoy: Decoy, image_schema_uid: UUID, slide_to_image: ImageToSampleRelation
) -> ImageSchema:
    image_schema = decoy.mock(cls=ImageSchema)
    decoy.when(image_schema.uid).then_return(image_schema_uid)
    decoy.when(image_schema.samples).then_return((slide_to_image,))
    return image_schema


@pytest.fixture()
def slide_schema(
    decoy: Decoy, slide_schema_uid: UUID, slide_to_image: ImageToSampleRelation
) -> SampleSchema:
    slide_schema = decoy.mock(cls=SampleSchema)
    decoy.when(slide_schema.uid).then_return(slide_schema_uid)
    decoy.when(slide_schema.children).then_return(())
    decoy.when(slide_schema.parents).then_return(())
    decoy.when(slide_schema.images).then_return((slide_to_image,))
    return slide_schema


@pytest.fixture()
def image_attributes_valid() -> bool:
    """Whether what is known about the image has been read from its file yet."""
    return False


@pytest.fixture()
def image(
    decoy: Decoy, image_schema_uid: UUID, image_attributes_valid: bool
) -> DatabaseImage:
    """An image as the metadata import leaves it: on its slide, with only what
    the source system filed it under."""
    image = decoy.mock(cls=DatabaseImage)
    decoy.when(image.uid).then_return(uuid4())
    decoy.when(image.identifier).then_return("PL1234-20-1")
    decoy.when(image.schema_uid).then_return(image_schema_uid)
    decoy.when(image.valid_attributes).then_return(image_attributes_valid)
    decoy.when(image.valid_relations).then_return(True)
    decoy.when(image.valid_pseudonym).then_return(True)
    decoy.when(image.failed).then_return(False)
    decoy.when(image.valid).then_return(image_attributes_valid)
    return image


@pytest.fixture()
def slide(decoy: Decoy, slide_schema_uid: UUID) -> DatabaseSample:
    """A slide nothing has been scanned for yet."""
    slide = decoy.mock(cls=DatabaseSample)
    decoy.when(slide.uid).then_return(uuid4())
    decoy.when(slide.identifier).then_return("PL1234-20-1")
    decoy.when(slide.schema_uid).then_return(slide_schema_uid)
    decoy.when(slide.valid_attributes).then_return(True)
    decoy.when(slide.valid_relations).then_return(False)
    decoy.when(slide.valid_pseudonym).then_return(True)
    decoy.when(slide.valid).then_return(False)
    return slide


@pytest.fixture()
def schema_service(
    decoy: Decoy,
    image_schema: ImageSchema,
    image_schema_uid: UUID,
    slide_schema: SampleSchema,
    slide_schema_uid: UUID,
) -> SchemaService:
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.images).then_return({image_schema_uid: image_schema})
    decoy.when(schema_service.samples).then_return({slide_schema_uid: slide_schema})
    return schema_service


@pytest.fixture()
def database_service(
    decoy: Decoy, session: Session, slide: DatabaseSample, image_schema_uid: UUID
) -> DatabaseService:
    database_service = decoy.mock(cls=DatabaseService)
    decoy.when(
        database_service.get_sample_images(session, slide, image_schema_uid)
    ).then_return([])
    return database_service


@pytest.fixture()
def validation_service(
    decoy: Decoy, schema_service: SchemaService, database_service: DatabaseService
) -> ValidationService:
    return ValidationService(
        schema_service=schema_service,
        database_service=database_service,
    )


@pytest.mark.unittest
class TestNonCompleteItems:
    """For an importer that brings in an item before what is known about it."""

    def test_an_image_awaiting_its_attributes_is_as_complete_as_expected(
        self,
        validation_service: ValidationService,
        image: DatabaseImage,
        image_schema_uid: UUID,
        session: Session,
    ) -> None:
        """The failure this guards against: every case in the batch flagged
        for images that are exactly as far along as they are supposed to be."""
        # Arrange
        completeness = MetadataImportCompleteness(
            non_complete_items=frozenset({image_schema_uid})
        )

        # Act
        complete = validation_service.item_is_as_complete_as_expected(
            image, completeness, session
        )

        # Assert
        assert complete

    def test_the_same_image_is_not_valid(
        self,
        validation_service: ValidationService,
        image: DatabaseImage,
        session: Session,
    ) -> None:
        """Excusing it says nothing about whether it is valid — the batch still
        refuses to complete on it, and a reviewer still cannot sign it off."""
        # Arrange
        completeness = MetadataImportCompleteness()

        # Act
        complete = validation_service.item_is_as_complete_as_expected(
            image, completeness, session
        )

        # Assert
        assert not complete
        assert not image.valid

    def test_relations_are_still_held_against_an_excused_image(
        self,
        decoy: Decoy,
        validation_service: ValidationService,
        image: DatabaseImage,
        image_schema_uid: UUID,
        session: Session,
    ) -> None:
        """Only the attributes were said to be late. An image that came in on
        no slide is wrong however little is yet known about it, and is what the
        import is being asked about."""
        # Arrange
        decoy.when(image.valid_relations).then_return(False)
        completeness = MetadataImportCompleteness(
            non_complete_items=frozenset({image_schema_uid})
        )

        # Act
        complete = validation_service.item_is_as_complete_as_expected(
            image, completeness, session
        )

        # Assert
        assert not complete

    @pytest.mark.parametrize("image_attributes_valid", [True])
    def test_an_image_that_has_everything_is_complete_either_way(
        self,
        validation_service: ValidationService,
        image: DatabaseImage,
        image_schema_uid: UUID,
        session: Session,
    ) -> None:
        # Arrange
        completeness = MetadataImportCompleteness(
            non_complete_items=frozenset({image_schema_uid})
        )

        # Act
        complete = validation_service.item_is_as_complete_as_expected(
            image, completeness, session
        )

        # Assert
        assert complete


@pytest.mark.unittest
class TestNonCompleteRelations:
    """For an importer that brings in the samples first and the images later."""

    def test_a_slide_awaiting_its_image_is_as_complete_as_expected(
        self,
        validation_service: ValidationService,
        slide: DatabaseSample,
        slide_to_image: ImageToSampleRelation,
        session: Session,
    ) -> None:
        """Counted again without the relation that nothing can satisfy yet:
        the stored answer is one boolean over every relation the slide has, so
        leaving one out cannot be read off it."""
        # Arrange
        completeness = MetadataImportCompleteness(
            non_complete_relations=frozenset({slide_to_image.uid})
        )

        # Act
        complete = validation_service.item_is_as_complete_as_expected(
            slide, completeness, session
        )

        # Assert
        assert complete

    def test_the_same_slide_is_not_valid(
        self,
        validation_service: ValidationService,
        slide: DatabaseSample,
        session: Session,
    ) -> None:
        """What was recorded on the slide is untouched by asking: it is still
        a slide with no image, and the batch will not complete on it."""
        # Arrange
        completeness = MetadataImportCompleteness()

        # Act
        complete = validation_service.item_is_as_complete_as_expected(
            slide, completeness, session
        )

        # Assert
        assert not complete
        assert not slide.valid_relations

    def test_a_relation_that_was_not_excused_still_counts(
        self,
        validation_service: ValidationService,
        slide: DatabaseSample,
        session: Session,
    ) -> None:
        """Excusing some other relation leaves this one to answer for itself."""
        # Arrange
        completeness = MetadataImportCompleteness(
            non_complete_relations=frozenset({uuid4()})
        )

        # Act
        complete = validation_service.item_is_as_complete_as_expected(
            slide, completeness, session
        )

        # Assert
        assert not complete


@pytest.mark.unittest
class TestValidForNow:
    """What the transition hook reads: validity as it is expected to stand
    right now, rather than validity outright. Asking for the plain answer
    while a batch is still importing would raise an issue on every case for
    images that have not been imported yet."""

    @pytest.fixture()
    def batch(self, decoy: Decoy) -> DatabaseBatch:
        """A batch whose images have not been processed yet."""
        batch = decoy.mock(cls=DatabaseBatch)
        decoy.when(batch.status).then_return(BatchStatus.METADATA_SEARCH_COMPLETE)
        return batch

    @pytest.fixture()
    def completeness(self, image_schema_uid: UUID) -> MetadataImportCompleteness:
        """What the metadata import does not bring in: the images' attributes,
        which are read from the files themselves."""
        return MetadataImportCompleteness(
            non_complete_items=frozenset({image_schema_uid})
        )

    @pytest.fixture()
    def review_unit(
        self, decoy: Decoy, completeness: MetadataImportCompleteness
    ) -> ReviewUnitSchema:
        review_unit = decoy.mock(cls=ReviewUnitSchema)
        decoy.when(review_unit.completeness).then_return(completeness)
        return review_unit

    def test_an_image_awaiting_its_attributes_is_valid_for_now(
        self,
        decoy: Decoy,
        validation_service: ValidationService,
        schema_service: SchemaService,
        review_unit: ReviewUnitSchema,
        image: DatabaseImage,
        batch: DatabaseBatch,
        session: Session,
    ) -> None:
        # Arrange
        decoy.when(schema_service.review_unit).then_return(review_unit)
        decoy.when(image.batch).then_return(batch)

        # Act
        valid_for_now = validation_service.item_is_valid_for_now(image, session)

        # Assert
        assert valid_for_now
        assert not image.valid

    def test_the_excuse_expires_once_the_images_are_in(
        self,
        decoy: Decoy,
        validation_service: ValidationService,
        schema_service: SchemaService,
        review_unit: ReviewUnitSchema,
        image: DatabaseImage,
        batch: DatabaseBatch,
        session: Session,
    ) -> None:
        """The same image, once the batch is far enough along for what was
        excused to have arrived: it now answers for itself."""
        # Arrange
        decoy.when(schema_service.review_unit).then_return(review_unit)
        decoy.when(image.batch).then_return(batch)
        decoy.when(batch.status).then_return(
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )

        # Act
        valid_for_now = validation_service.item_is_valid_for_now(image, session)

        # Assert
        assert not valid_for_now

    def test_a_unit_that_excuses_nothing_holds_the_item_to_plain_validity(
        self,
        decoy: Decoy,
        validation_service: ValidationService,
        schema_service: SchemaService,
        review_unit: ReviewUnitSchema,
        image: DatabaseImage,
        batch: DatabaseBatch,
        session: Session,
    ) -> None:
        # Arrange
        decoy.when(review_unit.completeness).then_return(None)
        decoy.when(schema_service.review_unit).then_return(review_unit)
        decoy.when(image.batch).then_return(batch)

        # Act
        valid_for_now = validation_service.item_is_valid_for_now(image, session)

        # Assert
        assert not valid_for_now

    def test_an_application_that_reviews_nothing_holds_it_to_plain_validity(
        self,
        decoy: Decoy,
        validation_service: ValidationService,
        schema_service: SchemaService,
        image: DatabaseImage,
        batch: DatabaseBatch,
        session: Session,
    ) -> None:
        # Arrange
        decoy.when(schema_service.review_unit).then_return(None)
        decoy.when(image.batch).then_return(batch)

        # Act
        valid_for_now = validation_service.item_is_valid_for_now(image, session)

        # Assert
        assert not valid_for_now

    def test_an_item_in_no_batch_is_held_to_plain_validity(
        self,
        decoy: Decoy,
        validation_service: ValidationService,
        schema_service: SchemaService,
        review_unit: ReviewUnitSchema,
        image: DatabaseImage,
        session: Session,
    ) -> None:
        """Nothing says how far along its import is supposed to be, so there is
        nothing to excuse it of."""
        # Arrange
        decoy.when(schema_service.review_unit).then_return(review_unit)
        decoy.when(image.batch).then_return(None)

        # Act
        valid_for_now = validation_service.item_is_valid_for_now(image, session)

        # Assert
        assert not valid_for_now

    def test_an_item_taken_out_of_the_project_is_valid_for_now(
        self,
        decoy: Decoy,
        validation_service: ValidationService,
        schema_service: SchemaService,
        review_unit: ReviewUnitSchema,
        image: DatabaseImage,
        batch: DatabaseBatch,
        session: Session,
    ) -> None:
        """One of the two ways of dealing with something that is not valid is
        taking it out of the project, and what is out of the project cannot be
        curated into anything. What a review unit answers for is read the same
        way."""
        # Arrange
        decoy.when(image.selected).then_return(False)
        decoy.when(schema_service.review_unit).then_return(review_unit)
        decoy.when(image.batch).then_return(batch)
        decoy.when(batch.status).then_return(
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )

        # Act
        valid_for_now = validation_service.item_is_valid_for_now(image, session)

        # Assert
        assert valid_for_now
        assert not image.valid

    def test_an_image_that_has_everything_is_valid_either_way(
        self,
        decoy: Decoy,
        validation_service: ValidationService,
        schema_service: SchemaService,
        review_unit: ReviewUnitSchema,
        image: DatabaseImage,
        batch: DatabaseBatch,
        session: Session,
    ) -> None:
        # Arrange
        decoy.when(image.valid).then_return(True)
        decoy.when(schema_service.review_unit).then_return(review_unit)
        decoy.when(image.batch).then_return(batch)
        decoy.when(batch.status).then_return(
            BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        )

        # Act
        valid_for_now = validation_service.item_is_valid_for_now(image, session)

        # Assert
        assert valid_for_now
