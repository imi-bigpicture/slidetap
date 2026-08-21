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

"""Tests for `ItemService`.

Run against a real database, since what is being pinned is what a sequence of
writes leaves behind, which is the part that broke.
"""

from collections.abc import Sequence
from contextlib import nullcontext
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from decoy import Decoy
from sqlalchemy.orm import Session

from slidetap.database import DatabaseImage, DatabaseSample
from slidetap.model import (
    Dataset,
    Image,
    ImageFormat,
    ImageSchema,
    ItemValueType,
    MetadataSearchResult,
    Project,
    ReviewIssueSource,
    RootSchema,
    Sample,
)
from slidetap.model.batch import BatchCreate
from slidetap.model.schema.attribute_value_layout import AttributeValueLayout
from slidetap.model.schema.hierarchy_layout import HierarchyLevelLayout
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ItemService,
    MapperService,
    ReviewService,
    SchemaService,
    TagService,
    ValidationService,
)

# ---------------------------------------------------------------------------
# Adding what a metadata search found
# ---------------------------------------------------------------------------


def _uid(identifier: str) -> UUID:
    """A uid that is the same every time the same thing is loaded.

    What the metadata import does, so that re-importing a case finds the items
    it wrote last time rather than writing them again.
    """
    return uuid5(NAMESPACE_URL, identifier)


@pytest.mark.integration
class TestAddSearchResultForAnExistingPatient:
    """A case imported for a patient the dataset already holds.

    An import hands its items over child-first -- every child is added, and
    validated, before the parent that claims it -- so a case is written while
    it still has no patient, and it is the patient being added afterwards that
    tells it that it has one. When the patient is already in the dataset that
    add is a lookup rather than an insert, and the branch that does the lookup
    used to return before validating anything. The case kept the invalid it was
    given while the patient was not there yet, for good.

    Two cases of one patient are what the metadata import produces all the
    time, either inside a batch or across two of them, so this is the ordinary
    path and not a corner of it.
    """

    @pytest.fixture()
    def item_service(
        self, sqlite_database_service: DatabaseService, schema: RootSchema
    ) -> ItemService:
        """The real thing on a real database, unlike the mocked one above."""
        schema_service = SchemaService(schema)
        validation_service = ValidationService(schema_service, sqlite_database_service)
        review_service = ReviewService(
            schema_service, validation_service, sqlite_database_service
        )
        attribute_service = AttributeService(
            schema_service, validation_service, sqlite_database_service, review_service
        )
        return ItemService(
            attribute_service,
            TagService(sqlite_database_service),
            MapperService(
                attribute_service,
                validation_service,
                schema_service,
                sqlite_database_service,
                review_service,
            ),
            schema_service,
            validation_service,
            sqlite_database_service,
            review_service,
        )

    @pytest.fixture()
    def schemas(self, schema: RootSchema) -> dict[str, UUID]:
        """The uids of the samples this builds a case out of, by name."""
        by_name = {sample.name: sample.uid for sample in schema.samples.values()}
        return {
            **{
                name: by_name[name]
                for name in ("slide", "block", "specimen", "case", "patient")
            },
            "image": next(iter(schema.images.values())).uid,
        }

    @pytest.fixture()
    def batches(
        self,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        project: Project,
    ) -> list[UUID]:
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_dataset(session, dataset)
            sqlite_database_service.add_project(session, project)
            return [
                sqlite_database_service.add_batch(
                    session, BatchCreate(name=name, project_uid=project.uid)
                ).uid
                for name in ("first", "second")
            ]

    @staticmethod
    def _items(
        schemas: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
        patient_identifier: str,
        case_identifier: str,
    ) -> list[Sample | Image]:
        """One patient, one case, and the chain down to a scanned image.

        Yielded child-first with the hierarchy carried on the parent's
        ``children`` -- the order and the shape the BigPicture metadata import
        hands over, which is what makes the patient the last item to be added.
        """

        def sample(schema_uid: UUID, identifier: str, **children: object) -> Sample:
            return Sample(
                uid=_uid(identifier),
                identifier=identifier,
                dataset_uid=dataset.uid,
                batch_uid=batch_uid,
                schema_uid=schema_uid,
                **children,  # type: ignore[arg-type]
            )

        slide_id = f"{case_identifier}-1-A-1"
        block_id = f"{case_identifier}-1-A"
        specimen_id = f"{case_identifier}-1"
        return [
            sample(schemas["slide"], slide_id),
            sample(
                schemas["block"],
                block_id,
                children={schemas["slide"]: [_uid(slide_id)]},
            ),
            sample(
                schemas["specimen"],
                specimen_id,
                children={schemas["block"]: [_uid(block_id)]},
            ),
            sample(
                schemas["case"],
                case_identifier,
                children={schemas["specimen"]: [_uid(specimen_id)]},
            ),
            sample(
                schemas["patient"],
                patient_identifier,
                children={schemas["case"]: [_uid(case_identifier)]},
            ),
            # After the patient, as the importer's own image search produces it.
            Image(
                uid=_uid(f"{slide_id}-image"),
                identifier=f"{slide_id}-image",
                dataset_uid=dataset.uid,
                batch_uid=batch_uid,
                schema_uid=schemas["image"],
                samples={schemas["slide"]: [_uid(slide_id)]},
                format=ImageFormat.DICOM_WSI,
            ),
        ]

    def _import(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
        patient_identifier: str,
        case_identifier: str,
    ) -> None:
        result = MetadataSearchResult.succeeded(
            identifier=case_identifier,
            schema_uid=schemas["case"],
            items=self._items(  # type: ignore[arg-type]
                schemas, dataset, batch_uid, patient_identifier, case_identifier
            ),
            item_uid=_uid(case_identifier),
        )
        with sqlite_database_service.get_session() as session:
            item_service.add_search_result(result, [], session=session)
            session.commit()

    def test_deleting_an_item_takes_what_was_raised_on_it_with_it(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batches: list[UUID],
    ):
        """The failure this guards against: a batch that cannot drop what a
        curator took out of the project, because something was raised on it
        while it was still in and the record points at it."""
        # Arrange
        self._import(
            item_service,
            sqlite_database_service,
            schemas,
            dataset,
            batches[0],
            "PAT-1",
            "PL1234-20",
        )
        case_uid = _uid("PL1234-20")
        slide_uid = _uid("PL1234-20-1-A-1")
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_review_issue(
                session,
                sqlite_database_service.get_item(session, slide_uid),
                sqlite_database_service.get_item(session, case_uid),
                "Not valid: relations",
                ReviewIssueSource.VALIDATION,
            )
            session.commit()

        # Act
        with sqlite_database_service.get_session() as session:
            session.delete(sqlite_database_service.get_item(session, slide_uid))
            session.commit()

        # Assert
        with sqlite_database_service.get_session() as session:
            assert (
                list(sqlite_database_service.get_review_issues(session, case_uid)) == []
            )

    @pytest.mark.parametrize(
        ("second_batch", "what"),
        [(False, "the same batch"), (True, "another batch")],
        ids=["same-batch", "other-batch"],
    )
    def test_second_case_of_a_patient_is_linked_and_valid(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batches: list[UUID],
        second_batch: bool,
        what: str,
    ):
        # Arrange: the patient is in the dataset, brought in by their first case.
        self._import(
            item_service,
            sqlite_database_service,
            schemas,
            dataset,
            batches[0],
            "PATIENT-1",
            "CASE-A",
        )
        first = item_service.get_sample(_uid("CASE-A"))
        assert first.valid_relations, (
            "the first case of a new patient should come out valid -- if this "
            "fails the chain built by this test is incomplete, not the code"
        )

        # Act: a second case of the same patient, so the patient is found
        # rather than inserted.
        self._import(
            item_service,
            sqlite_database_service,
            schemas,
            dataset,
            batches[1] if second_batch else batches[0],
            "PATIENT-1",
            "CASE-B",
        )

        # Assert
        second = item_service.get_sample(_uid("CASE-B"))
        assert second.parents[schemas["patient"]] == [_uid("PATIENT-1")], (
            f"a case imported into {what} should hang from the patient already "
            f"in the dataset"
        )
        assert second.valid_relations, (
            f"a case imported into {what} for a patient already in the dataset "
            f"should not be left marked as having no patient"
        )

    def test_the_patient_holds_both_cases(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batches: list[UUID],
    ):
        # Arrange / Act
        for batch_uid, case_identifier in (
            (batches[0], "CASE-A"),
            (batches[1], "CASE-B"),
        ):
            self._import(
                item_service,
                sqlite_database_service,
                schemas,
                dataset,
                batch_uid,
                "PATIENT-1",
                case_identifier,
            )

        # Assert: one patient, not one per case, holding both.
        patient = item_service.get_sample(_uid("PATIENT-1"))
        assert sorted(patient.children[schemas["case"]]) == sorted(
            [_uid("CASE-A"), _uid("CASE-B")]
        )
        assert patient.valid_relations


@pytest.mark.unittest
class TestMovingAnAttributeBetweenItems:
    """Moving a value takes it off one item and puts it on the other, so one
    can become valid while the other stops being. Both ends have to say so, and
    both have to be read before the move — afterwards there is no telling what
    either of them was."""

    @pytest.fixture()
    def session(self, decoy: Decoy) -> Session:
        return decoy.mock(cls=Session)

    @pytest.fixture()
    def schema_uid(self) -> UUID:
        return uuid4()

    @pytest.fixture()
    def source(self, decoy: Decoy, schema_uid: UUID) -> DatabaseSample:
        """The specimen the diagnosis was filed under, wrongly."""
        source = decoy.mock(cls=DatabaseSample)
        decoy.when(source.uid).then_return(uuid4())
        decoy.when(source.schema_uid).then_return(schema_uid)
        return source

    @pytest.fixture()
    def target(self, decoy: Decoy, schema_uid: UUID) -> DatabaseSample:
        """The one it belongs to."""
        target = decoy.mock(cls=DatabaseSample)
        decoy.when(target.uid).then_return(uuid4())
        decoy.when(target.schema_uid).then_return(schema_uid)
        return target

    @pytest.fixture()
    def database_service(
        self,
        decoy: Decoy,
        session: Session,
        source: DatabaseSample,
        target: DatabaseSample,
    ) -> DatabaseService:
        database_service = decoy.mock(cls=DatabaseService)
        decoy.when(database_service.get_session(None)).then_return(nullcontext(session))
        decoy.when(database_service.get_item(session, source.uid)).then_return(source)
        decoy.when(database_service.get_item(session, target.uid)).then_return(target)
        return database_service

    @pytest.fixture()
    def validation_service(
        self,
        decoy: Decoy,
        session: Session,
        source: DatabaseSample,
        target: DatabaseSample,
    ) -> ValidationService:
        """The move fixes the target and breaks the source, read in that order:
        once before the move and once after, for each of them."""
        validation_service = decoy.mock(cls=ValidationService)
        decoy.when(
            validation_service.item_is_valid_for_now(source, session)
        ).then_return(True, False)
        decoy.when(
            validation_service.item_is_valid_for_now(target, session)
        ).then_return(False, True)
        return validation_service

    @pytest.fixture()
    def review_service(self, decoy: Decoy) -> ReviewService:
        return decoy.mock(cls=ReviewService)

    @pytest.fixture()
    def item_service(
        self,
        decoy: Decoy,
        database_service: DatabaseService,
        validation_service: ValidationService,
        review_service: ReviewService,
    ) -> ItemService:
        return ItemService(
            decoy.mock(cls=AttributeService),
            decoy.mock(cls=TagService),
            decoy.mock(cls=MapperService),
            decoy.mock(cls=SchemaService),
            validation_service,
            database_service,
            review_service,
        )

    def test_both_ends_report_what_the_move_did_to_them(
        self,
        decoy: Decoy,
        session: Session,
        item_service: ItemService,
        review_service: ReviewService,
        source: DatabaseSample,
        target: DatabaseSample,
    ):
        """The failure this guards against: the case the diagnosis was moved to
        stays flagged for a specimen that is now filled in, and the case it was
        moved off is never raised on for the hole it left."""
        # Arrange

        # Act
        item_service.move_attribute(source.uid, "diagnose", target.uid)

        # Assert
        decoy.verify(
            review_service.item_validity_changed(
                source.uid, True, False, session=session
            ),
            times=1,
        )
        decoy.verify(
            review_service.item_validity_changed(
                target.uid, False, True, session=session
            ),
            times=1,
        )


@pytest.mark.unittest
class TestMovingAnItemToAnotherParent:
    """An image PACS could not place is parked on the case, and moving it onto
    the slide it is of is what makes that slide valid. Validating the moved
    item validates the other side of its relations, so both it and the parent
    it lands on have to say what that did to them."""

    @pytest.fixture()
    def session(self, decoy: Decoy) -> Session:
        return decoy.mock(cls=Session)

    @pytest.fixture()
    def image_schema_uid(self) -> UUID:
        return uuid4()

    @pytest.fixture()
    def wrong_slide(self, decoy: Decoy) -> DatabaseSample:
        """The slide the image was filed under, which has nothing else scanned
        for it."""
        wrong_slide = decoy.mock(cls=DatabaseSample)
        decoy.when(wrong_slide.uid).then_return(uuid4())
        decoy.when(wrong_slide.identifier).then_return("PL1234-20-1-A-2")
        return wrong_slide

    @pytest.fixture()
    def parked_image(
        self, decoy: Decoy, image_schema_uid: UUID, wrong_slide: DatabaseSample
    ) -> DatabaseImage:
        image = decoy.mock(cls=DatabaseImage)
        decoy.when(image.uid).then_return(uuid4())
        decoy.when(image.identifier).then_return("PL1234-20-1-A-1")
        decoy.when(image.schema_uid).then_return(image_schema_uid)
        decoy.when(image.locked).then_return(False)
        decoy.when(image.samples).then_return({wrong_slide})
        return image

    @pytest.fixture()
    def slide(self, decoy: Decoy) -> DatabaseSample:
        """The slide the image turns out to be of, waiting on it to be valid."""
        slide = decoy.mock(cls=DatabaseSample)
        decoy.when(slide.uid).then_return(uuid4())
        decoy.when(slide.identifier).then_return("PL1234-20-1-A-1")
        return slide

    @pytest.fixture()
    def slide_model(self, slide: DatabaseSample) -> Sample:
        """The slide as the parent check hands it back: a model, not a row."""
        return Sample(
            uid=slide.uid,
            identifier=slide.identifier,
            dataset_uid=uuid4(),
            batch_uid=uuid4(),
            schema_uid=uuid4(),
        )

    @pytest.fixture()
    def item_service(
        self,
        decoy: Decoy,
        session: Session,
        parked_image: DatabaseImage,
        slide: DatabaseSample,
        slide_model: Sample,
        image_schema_uid: UUID,
        review_service: ReviewService,
        validation_service: ValidationService,
    ) -> ItemService:
        image_schema = decoy.mock(cls=ImageSchema)
        database_service = decoy.mock(cls=DatabaseService)
        decoy.when(database_service.get_session(None)).then_return(nullcontext(session))
        decoy.when(database_service.get_item(session, parked_image.uid)).then_return(
            parked_image
        )
        decoy.when(database_service.get_item(session, slide.uid)).then_return(slide)
        decoy.when(database_service.get_sample(session, slide.uid)).then_return(slide)
        decoy.when(slide.schema_uid).then_return(slide_model.schema_uid)
        decoy.when(slide.model).then_return(slide_model)
        schema_service = decoy.mock(cls=SchemaService)
        decoy.when(schema_service.items).then_return({image_schema_uid: image_schema})
        # One slide holds the image, which is what the parent check reads to
        # decide the move is allowed at all.
        decoy.when(schema_service.parent_schema_caps(image_schema)).then_return(
            {slide_model.schema_uid: 1}
        )
        return ItemService(
            decoy.mock(cls=AttributeService),
            decoy.mock(cls=TagService),
            decoy.mock(cls=MapperService),
            schema_service,
            validation_service,
            database_service,
            review_service,
        )

    @pytest.fixture()
    def review_service(self, decoy: Decoy) -> ReviewService:
        return decoy.mock(cls=ReviewService)

    @pytest.fixture()
    def validation_service(
        self,
        decoy: Decoy,
        session: Session,
        parked_image: DatabaseImage,
        slide_model: Sample,
        wrong_slide: DatabaseSample,
    ) -> ValidationService:
        """The move settles both of them: the image was on the wrong parent and
        the slide had nothing scanned for it. Read once before and once after,
        for each."""
        validation_service = decoy.mock(cls=ValidationService)
        decoy.when(
            validation_service.item_is_valid_for_now(parked_image, session)
        ).then_return(False, True)
        decoy.when(
            validation_service.item_is_valid_for_now(slide_model, session)
        ).then_return(False, True)
        # And leaves the slide it was filed under with nothing scanned for it.
        decoy.when(
            validation_service.item_is_valid_for_now(wrong_slide, session)
        ).then_return(True, False)
        return validation_service

    def test_the_item_and_both_parents_report(
        self,
        decoy: Decoy,
        session: Session,
        item_service: ItemService,
        review_service: ReviewService,
        parked_image: DatabaseImage,
        slide: DatabaseSample,
        wrong_slide: DatabaseSample,
    ):
        """The failure this guards against, at both ends: the image is put
        where it belongs and the case stays flagged for a slide that now has
        everything, while the slide it was taken off is left with nothing
        scanned for it and nobody is told."""
        # Arrange

        # Act
        item_service.move_to_parent(parked_image.uid, slide.uid)

        # Assert
        decoy.verify(
            review_service.item_validity_changed(
                parked_image.uid, False, True, session=session
            ),
            times=1,
        )
        decoy.verify(
            review_service.item_validity_changed(
                slide.uid, False, True, session=session
            ),
            times=1,
        )
        decoy.verify(
            review_service.item_validity_changed(
                wrong_slide.uid, True, False, session=session
            ),
            times=1,
        )


# ---------------------------------------------------------------------------
# What a row of the tree says
# ---------------------------------------------------------------------------


class TestHierarchyRowAttributes:
    """A level shows the attributes it names, and nothing else.

    Where an item keeps the named attribute is not the level's business: an
    image carries what PACS filed it under as private attributes, and reading
    one of those beside the slide the image hangs under is how a curator works
    out which slide an unplaced image is of.
    """

    @staticmethod
    def _attribute(tag: str) -> object:
        """Enough of a database attribute for the lookup: a tag and a model."""
        return type("Attribute", (), {"tag": tag, "model": f"{tag} value"})()

    def _item(self, tags: Sequence[str], private_tags: Sequence[str]) -> object:
        return type(
            "Item",
            (),
            {
                "attributes": {self._attribute(tag) for tag in tags},
                "private_attributes": {self._attribute(tag) for tag in private_tags},
            },
        )()

    def test_a_named_private_attribute_is_shown(self):
        # Arrange
        item = self._item(tags=["staining"], private_tags=["pacs_staining"])
        level = HierarchyLevelLayout(
            schema_uid=uuid4(),
            attributes=[
                AttributeValueLayout(tag="staining"),
                AttributeValueLayout(tag="pacs_staining"),
            ],
        )

        # Act
        attributes = ItemService._layout_attributes(item, level)  # type: ignore[arg-type]

        # Assert
        assert list(attributes) == ["staining", "pacs_staining"]

    def test_an_attribute_the_level_does_not_name_is_not_shown(self):
        """Including the private ones: naming is what asks for them."""
        # Arrange
        item = self._item(tags=["staining"], private_tags=["pacs_exam_id"])
        level = HierarchyLevelLayout(
            schema_uid=uuid4(), attributes=[AttributeValueLayout(tag="staining")]
        )

        # Act
        attributes = ItemService._layout_attributes(item, level)  # type: ignore[arg-type]

        # Assert
        assert list(attributes) == ["staining"]


@pytest.mark.unittest
class TestWhetherARowIsStillInTheProject:
    """A row says whether its item is still part of the project, and whether
    that is still a question.

    Taking something out of the project is a flag rather than a deletion, and
    the row it was taken out from is where it is put back -- so the tree has to
    carry the flag, or the row that a curator has just taken out looks exactly
    like the rows they have not. A locked batch has had the question answered
    for it, and the row carries that too, so that what would be refused is not
    offered.
    """

    @pytest.fixture()
    def schema_service(self, schema: RootSchema) -> SchemaService:
        return SchemaService(schema)

    @pytest.fixture()
    def sample_schema_uid(self, schema: RootSchema) -> UUID:
        return next(iter(schema.samples.values())).uid

    @pytest.fixture()
    def database_service(self, decoy: Decoy) -> DatabaseService:
        return decoy.mock(cls=DatabaseService)

    @pytest.fixture()
    def item_service(
        self,
        decoy: Decoy,
        schema_service: SchemaService,
        database_service: DatabaseService,
    ) -> ItemService:
        return ItemService(
            decoy.mock(cls=AttributeService),
            decoy.mock(cls=TagService),
            decoy.mock(cls=MapperService),
            schema_service,
            decoy.mock(cls=ValidationService),
            database_service,
            decoy.mock(cls=ReviewService),
        )

    @pytest.mark.parametrize("locked", [True, False])
    @pytest.mark.parametrize("selected", [True, False])
    def test_the_row_carries_the_flags(
        self,
        decoy: Decoy,
        item_service: ItemService,
        database_service: DatabaseService,
        sample_schema_uid: UUID,
        selected: bool,
        locked: bool,
    ):
        # Arrange: a slide with nothing hanging under it, which is the one a
        # curator is offered the choice about.
        item = decoy.mock(cls=DatabaseSample)
        decoy.when(item.uid).then_return(uuid4())
        decoy.when(item.identifier).then_return("SLIDE-1")
        decoy.when(item.name).then_return(None)
        decoy.when(item.pseudonym).then_return(None)
        decoy.when(item.schema_uid).then_return(sample_schema_uid)
        decoy.when(item.item_value_type).then_return(ItemValueType.SAMPLE)
        decoy.when(item.valid).then_return(False)
        decoy.when(item.selected).then_return(selected)
        decoy.when(item.locked).then_return(locked)
        decoy.when(database_service.get_children(item)).then_return([])

        # Act
        node = item_service._build_hierarchy_node(
            item, orphan=False, ancestors=frozenset(), levels={}
        )

        # Assert
        assert node.selected is selected
        assert node.locked is locked
        assert node.children == []
