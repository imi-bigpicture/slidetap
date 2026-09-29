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

"""Tests for what follows an item into or out of the project.

What follows is read off the schema's cardinalities, so the schema here is
the whole story: a patient of cases of specimens of blocks of slides, each
level requiring at least one of the next; a diagnosis on the case that the
case may or may not require; a macro image over blocks; a block that may
come from more than one specimen.
"""

from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from decoy import Decoy, matchers

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
    NotAllowedActionError,
)
from slidetap.model import Cardinality, Dataset, ImageFormat, Project
from slidetap.model.batch import BatchCreate
from slidetap.model.item_select import (
    CascadeDirection,
    ItemBulkSelect,
    ItemSelect,
    SelectionChange,
    SelectionTree,
    SelectionTreeNode,
)
from slidetap.model.schema.dataset_schema import DatasetSchema
from slidetap.model.schema.item_relation import (
    AnnotationToImageRelation,
    ImageToSampleRelation,
    ObservationToAnnotationRelation,
    ObservationToImageRelation,
    ObservationToSampleRelation,
    SampleToSampleRelation,
)
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.model.schema.project_schema import ProjectSchema
from slidetap.model.schema.root_schema import RootSchema
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


class Uids:
    """The schema uids, named so a test reads as the hierarchy it builds."""

    patient = uuid4()
    case = uuid4()
    specimen = uuid4()
    block = uuid4()
    slide = uuid4()
    image = uuid4()
    macro = uuid4()
    annotation = uuid4()
    diagnosis = uuid4()
    finding = uuid4()
    image_note = uuid4()


@pytest.fixture()
def diagnoses_cardinality() -> Cardinality:
    """Whether a case is anything without a diagnosis."""
    return Cardinality.ZERO_OR_MORE


@pytest.fixture()
def schema(diagnoses_cardinality: Cardinality) -> RootSchema:
    def sample_to_sample(
        parent: UUID, child: UUID, parents: Cardinality
    ) -> SampleToSampleRelation:
        return SampleToSampleRelation(
            uid=uuid4(),
            name=f"{parent} to {child}",
            parent_uid=parent,
            child_uid=child,
            parents=parents,
            children=Cardinality.ONE_OR_MORE,
            parent_title="Parent",
            child_title="Child",
        )

    patient_to_case = sample_to_sample(Uids.patient, Uids.case, Cardinality.ONE)
    case_to_specimen = sample_to_sample(Uids.case, Uids.specimen, Cardinality.ONE)
    # A specimen may also be related to its patient directly, as the
    # BigPicture schema relates it to its being. Required on neither side, so
    # it only matters where an item uses it.
    patient_to_specimen = SampleToSampleRelation(
        uid=uuid4(),
        name="patient to specimen",
        parent_uid=Uids.patient,
        child_uid=Uids.specimen,
        parents=Cardinality.ZERO_OR_MORE,
        children=Cardinality.ZERO_OR_MORE,
        parent_title="Patient",
        child_title="Specimens",
    )
    specimen_to_block = sample_to_sample(
        Uids.specimen, Uids.block, Cardinality.ONE_OR_MORE
    )
    block_to_slide = sample_to_sample(Uids.block, Uids.slide, Cardinality.ONE)
    slide_to_image = ImageToSampleRelation(
        uid=uuid4(),
        name="Image of slide",
        image_uid=Uids.image,
        sample_uid=Uids.slide,
        images=Cardinality.ONE_OR_MORE,
        samples=Cardinality.ONE,
        image_title="WSI",
        sample_title="Slide",
    )
    block_to_macro = ImageToSampleRelation(
        uid=uuid4(),
        name="Macro image of blocks",
        image_uid=Uids.macro,
        sample_uid=Uids.block,
        images=Cardinality.ZERO_OR_MORE,
        samples=Cardinality.ONE_OR_MORE,
        image_title="Macro",
        sample_title="Block",
    )
    image_to_annotation = AnnotationToImageRelation(
        uid=uuid4(),
        name="Annotation on image",
        annotation_uid=Uids.annotation,
        image_uid=Uids.image,
        annotation_title="Annotation",
        image_title="WSI",
    )
    case_to_diagnosis = ObservationToSampleRelation(
        uid=uuid4(),
        name="Diagnosis of case",
        observation_uid=Uids.diagnosis,
        sample_uid=Uids.case,
        observation_title="Diagnosis",
        sample_title="Case",
        observations=diagnoses_cardinality,
    )
    annotation_to_finding = ObservationToAnnotationRelation(
        uid=uuid4(),
        name="Finding of annotation",
        observation_uid=Uids.finding,
        annotation_uid=Uids.annotation,
        observation_title="Finding",
        annotation_title="Annotation",
    )
    image_to_note = ObservationToImageRelation(
        uid=uuid4(),
        name="Note on image",
        observation_uid=Uids.image_note,
        image_uid=Uids.image,
        observation_title="Note",
        image_title="WSI",
    )

    def sample(
        uid: UUID,
        name: str,
        order: int,
        children: Iterable[SampleToSampleRelation] = (),
        parents: Iterable[SampleToSampleRelation] = (),
        images: Iterable[ImageToSampleRelation] = (),
        observations: Iterable[ObservationToSampleRelation] = (),
    ) -> SampleSchema:
        return SampleSchema(
            uid=uid,
            name=name,
            display_name=name,
            display_order=order,
            children=tuple(children),
            parents=tuple(parents),
            images=tuple(images),
            observations=tuple(observations),
        )

    return RootSchema(
        uid=uuid4(),
        name="Selection cascade",
        project=ProjectSchema(
            uid=uuid4(), name="project", display_name="Project", attributes={}
        ),
        dataset=DatasetSchema(
            uid=uuid4(), name="dataset", display_name="Dataset", attributes={}
        ),
        samples={
            Uids.patient: sample(
                Uids.patient, "patient", 0, [patient_to_case, patient_to_specimen]
            ),
            Uids.case: sample(
                Uids.case,
                "case",
                1,
                [case_to_specimen],
                [patient_to_case],
                observations=[case_to_diagnosis],
            ),
            Uids.specimen: sample(
                Uids.specimen,
                "specimen",
                2,
                [specimen_to_block],
                [case_to_specimen, patient_to_specimen],
            ),
            Uids.block: sample(
                Uids.block,
                "block",
                3,
                [block_to_slide],
                [specimen_to_block],
                images=[block_to_macro],
            ),
            Uids.slide: sample(
                Uids.slide, "slide", 4, (), [block_to_slide], images=[slide_to_image]
            ),
        },
        images={
            Uids.image: ImageSchema(
                uid=Uids.image,
                name="wsi",
                display_name="WSI",
                display_order=5,
                samples=(slide_to_image,),
                annotations=(image_to_annotation,),
                observations=(image_to_note,),
            ),
            Uids.macro: ImageSchema(
                uid=Uids.macro,
                name="macro",
                display_name="Macro",
                display_order=6,
                samples=(block_to_macro,),
            ),
        },
        annotations={
            Uids.annotation: AnnotationSchema(
                uid=Uids.annotation,
                name="annotation",
                display_name="Annotation",
                display_order=7,
                images=(image_to_annotation,),
                observations=(annotation_to_finding,),
            )
        },
        observations={
            Uids.diagnosis: ObservationSchema(
                uid=Uids.diagnosis,
                name="diagnosis",
                display_name="Diagnosis",
                display_order=8,
                samples=(case_to_diagnosis,),
            ),
            Uids.finding: ObservationSchema(
                uid=Uids.finding,
                name="finding",
                display_name="Finding",
                display_order=9,
                annotations=(annotation_to_finding,),
            ),
            Uids.image_note: ObservationSchema(
                uid=Uids.image_note,
                name="note",
                display_name="Note",
                display_order=10,
                images=(image_to_note,),
            ),
        },
    )


@pytest.fixture()
def batch_uid(
    sqlite_database_service: DatabaseService, dataset: Dataset, project: Project
) -> UUID:
    with sqlite_database_service.get_session() as session:
        sqlite_database_service.add_dataset(session, dataset)
        sqlite_database_service.add_project(session, project)
        return sqlite_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        ).uid


@pytest.fixture()
def validation_service(
    sqlite_database_service: DatabaseService, schema: RootSchema
) -> ValidationService:
    return ValidationService(SchemaService(schema), sqlite_database_service)


@pytest.fixture()
def item_service(
    sqlite_database_service: DatabaseService,
    schema: RootSchema,
    validation_service: ValidationService,
) -> ItemService:
    schema_service = SchemaService(schema)
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


class Hierarchy:
    """One patient with everything under it, by name.

    patient
      case (diagnosis)
        specimen_1, specimen_2
          block (from both specimens, with a macro image)
            slide_1 (image_1 with an annotation, a finding and a note)
            slide_2 (image_2)
    """

    def __init__(self, dataset: Dataset, batch_uid: UUID):
        def sample(schema_uid: UUID, name: str, **kwargs) -> DatabaseSample:
            return DatabaseSample(dataset.uid, batch_uid, schema_uid, name, **kwargs)

        self.patient = sample(Uids.patient, "patient")
        self.case = sample(Uids.case, "case", parents=self.patient)
        self.diagnosis = DatabaseObservation(
            dataset.uid, batch_uid, Uids.diagnosis, "diagnosis", item=self.case
        )
        self.specimen_1 = sample(Uids.specimen, "specimen_1", parents=self.case)
        self.specimen_2 = sample(Uids.specimen, "specimen_2", parents=self.case)
        self.block = sample(
            Uids.block, "block", parents=[self.specimen_1, self.specimen_2]
        )
        self.macro = DatabaseImage(
            dataset.uid,
            batch_uid,
            Uids.macro,
            "macro",
            ImageFormat.OTHER_WSI,
            samples=self.block,
        )
        self.slide_1 = sample(Uids.slide, "slide_1", parents=self.block)
        self.slide_2 = sample(Uids.slide, "slide_2", parents=self.block)
        self.image_1 = DatabaseImage(
            dataset.uid,
            batch_uid,
            Uids.image,
            "image_1",
            ImageFormat.OTHER_WSI,
            samples=self.slide_1,
        )
        self.image_2 = DatabaseImage(
            dataset.uid,
            batch_uid,
            Uids.image,
            "image_2",
            ImageFormat.OTHER_WSI,
            samples=self.slide_2,
        )
        self.annotation = DatabaseAnnotation(
            dataset.uid, batch_uid, Uids.annotation, "annotation", image=self.image_1
        )
        self.finding = DatabaseObservation(
            dataset.uid, batch_uid, Uids.finding, "finding", item=self.annotation
        )
        self.note = DatabaseObservation(
            dataset.uid, batch_uid, Uids.image_note, "note", item=self.image_1
        )

    @property
    def items(self) -> dict[str, DatabaseItem]:
        return {
            name: item
            for name, item in vars(self).items()
            if isinstance(item, DatabaseItem)
        }


@pytest.fixture()
def hierarchy(
    sqlite_database_service: DatabaseService, dataset: Dataset, batch_uid: UUID
) -> dict[str, UUID]:
    """The hierarchy stored, as the uid of each item by name."""
    with sqlite_database_service.get_session() as session:
        built = Hierarchy(dataset, batch_uid)
        session.add(built.patient)
        session.commit()
        return {name: item.uid for name, item in built.items.items()}


def _selected(
    sqlite_database_service: DatabaseService, hierarchy: dict[str, UUID]
) -> set[str]:
    """The names of what is in the project."""
    with sqlite_database_service.get_session() as session:
        return {
            name
            for name, uid in hierarchy.items()
            if sqlite_database_service.get_item(session, uid).selected
        }


def _valid_relations(
    sqlite_database_service: DatabaseService, hierarchy: dict[str, UUID], name: str
) -> bool:
    with sqlite_database_service.get_session() as session:
        return bool(
            sqlite_database_service.get_item(session, hierarchy[name]).valid_relations
        )


def _curator_excluded(
    sqlite_database_service: DatabaseService, hierarchy: dict[str, UUID]
) -> set[str]:
    """The names of what a curator took out by name."""
    with sqlite_database_service.get_session() as session:
        return {
            name
            for name, uid in hierarchy.items()
            if sqlite_database_service.get_item(session, uid).curator_excluded
        }


def _forget_curation(
    sqlite_database_service: DatabaseService, hierarchy: dict[str, UUID]
) -> None:
    """Clear every curation mark, as if everything out had gone with
    something else rather than by name."""
    with sqlite_database_service.get_session() as session:
        for uid in hierarchy.values():
            sqlite_database_service.get_item(session, uid).curator_excluded = False
        session.commit()


@pytest.mark.unittest
class TestDeselecting:
    def test_a_slide_goes_with_its_image_and_nothing_above_it(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """The block still has a slide, so it and everything above it stay,
        diagnosis included. Issue #77 was this taking the diagnosis."""
        # Arrange
        everything = set(hierarchy)

        # Act
        item_service.select_item(hierarchy["slide_1"], False)

        # Assert
        gone = {"slide_1", "image_1", "annotation", "finding", "note"}
        assert _selected(sqlite_database_service, hierarchy) == everything - gone

    def test_the_last_slide_takes_the_block_and_everything_above_with_it(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """Every level requires at least one of the next, so nothing above is
        left standing, and what hung on those levels goes too."""
        # Arrange
        item_service.select_item(hierarchy["slide_1"], False)

        # Act
        item_service.select_item(hierarchy["slide_2"], False)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == set()

    def test_the_last_image_takes_its_slide(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """A slide requires an image, so a slide with no image left is not
        one, and it goes the same way the block goes with its last slide."""
        # Arrange
        everything = set(hierarchy)

        # Act
        item_service.select_item(hierarchy["image_2"], False)

        # Assert
        gone = {"image_2", "slide_2"}
        assert _selected(sqlite_database_service, hierarchy) == everything - gone

    def test_a_macro_image_stays_while_one_of_its_blocks_is_in(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
    ):
        """The macro image is over two blocks and needs one of them."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            block = sqlite_database_service.get_sample(session, hierarchy["block"])
            other_block = DatabaseSample(
                dataset.uid,
                batch_uid,
                Uids.block,
                "other_block",
                parents=list(block.parents),
            )
            session.add(other_block)
            session.add(
                DatabaseSample(
                    dataset.uid,
                    batch_uid,
                    Uids.slide,
                    "other_slide",
                    parents=other_block,
                )
            )
            macro = sqlite_database_service.get_image(session, hierarchy["macro"])
            macro.samples.add(other_block)
            session.commit()
            hierarchy["other_block"] = other_block.uid

        # Act
        item_service.select_item(hierarchy["other_block"], False)

        # Assert
        assert "macro" in _selected(sqlite_database_service, hierarchy)

    def test_a_block_stays_while_one_of_its_specimens_is_in(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        everything = set(hierarchy)

        # Act
        item_service.select_item(hierarchy["specimen_1"], False)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == everything - {
            "specimen_1"
        }

    def test_a_block_goes_with_the_last_of_its_specimens(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        item_service.select_item(hierarchy["specimen_1"], False)

        # Act
        item_service.select_item(hierarchy["specimen_2"], False)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == set()

    def test_a_diagnosis_goes_alone(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        everything = set(hierarchy)

        # Act
        item_service.select_item(hierarchy["diagnosis"], False)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == everything - {
            "diagnosis"
        }

    @pytest.mark.parametrize("diagnoses_cardinality", [Cardinality.ONE_OR_MORE])
    def test_a_case_that_needs_a_diagnosis_goes_with_the_last_one(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """A diagnosis is a requirement like any other: the case is not a case
        without one, and the patient is not one without the case."""
        # Arrange

        # Act
        item_service.select_item(hierarchy["diagnosis"], False)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == set()

    def test_what_is_left_short_by_a_selection_is_marked_not_valid(
        self,
        item_service: ItemService,
        validation_service: ValidationService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """Selecting a slide brings its block, but not the block's other
        slide. The block is valid either way; the slide that was selected is,
        and so is everything the cascade brought in with it."""
        # Arrange
        item_service.select_item(hierarchy["case"], False)
        _forget_curation(sqlite_database_service, hierarchy)

        # Act
        item_service.select_item(hierarchy["slide_1"], True)

        # Assert
        for name in ("slide_1", "image_1", "block", "specimen_1", "case", "patient"):
            assert _valid_relations(sqlite_database_service, hierarchy, name), name

    def test_nothing_moves_when_a_locked_item_would(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        item_service.select_item(hierarchy["slide_1"], False)
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.get_item(session, hierarchy["block"]).locked = True
            session.commit()
        before = _selected(sqlite_database_service, hierarchy)

        # Act
        with pytest.raises(NotAllowedActionError):
            item_service.select_item(hierarchy["slide_2"], False)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == before


@pytest.mark.unittest
class TestSelecting:
    @pytest.fixture()
    def hierarchy(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ) -> dict[str, UUID]:
        """The hierarchy with everything out, and none of it by name, so that
        what a selection brings back is only what the schema asks for."""
        item_service.select_item(hierarchy["case"], False)
        _forget_curation(sqlite_database_service, hierarchy)
        assert _selected(sqlite_database_service, hierarchy) == set()
        return hierarchy

    def test_a_slide_brings_what_it_needs_and_nothing_else(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """Up: the block, its specimens, the case. Down: an image, since a
        slide needs one. Not: the other slide, the macro image, what was on
        the image, or the diagnosis the case does not require."""
        # Arrange

        # Act
        item_service.select_item(hierarchy["slide_1"], True)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == {
            "patient",
            "case",
            "specimen_1",
            "specimen_2",
            "block",
            "slide_1",
            "image_1",
        }

    @pytest.mark.parametrize("diagnoses_cardinality", [Cardinality.ONE_OR_MORE])
    def test_a_case_that_needs_a_diagnosis_brings_it_back(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        item_service.select_item(hierarchy["slide_1"], True)

        # Assert
        assert "diagnosis" in _selected(sqlite_database_service, hierarchy)

    def test_a_case_brings_back_what_the_schema_says_a_case_is_made_of(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """Every level requires the next, down to the images. Annotations,
        notes, findings and the macro image are allowed but not required, and
        stay out."""
        # Arrange

        # Act
        item_service.select_item(hierarchy["case"], True)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == {
            "patient",
            "case",
            "specimen_1",
            "specimen_2",
            "block",
            "slide_1",
            "slide_2",
            "image_1",
            "image_2",
        }

    def test_a_finding_brings_its_annotation_and_the_image_and_slide_it_is_on(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        item_service.select_item(hierarchy["finding"], True)

        # Assert
        selected = _selected(sqlite_database_service, hierarchy)
        assert {"finding", "annotation", "image_1", "slide_1", "block", "case"} <= (
            selected
        )
        assert "slide_2" not in selected

    def test_a_macro_image_brings_a_block_to_be_over(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        item_service.select_item(hierarchy["macro"], True)

        # Assert
        assert {"macro", "block"} <= _selected(sqlite_database_service, hierarchy)


def _request(select: bool, **options) -> ItemSelect:
    return ItemSelect(select=select, **options)


def _names(hierarchy: dict[str, UUID], changes: Iterable[SelectionChange]) -> set[str]:
    by_uid = {uid: name for name, uid in hierarchy.items()}
    return {by_uid[change.uid] for change in changes}


@pytest.mark.unittest
class TestCuration:
    def test_what_is_taken_out_by_name_is_marked_and_what_goes_with_it_is_not(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        item_service.select(hierarchy["slide_1"], _request(False))

        # Assert
        assert _curator_excluded(sqlite_database_service, hierarchy) == {"slide_1"}

    def test_bringing_back_a_block_leaves_its_slides_taken_out_by_name(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """Both slides were taken out by name, and the block and everything
        above went with the last of them. A block needs a slide, and without
        the marks selecting it would bring both back. With them, it reports
        them kept out and leaves the block short."""
        # Arrange
        item_service.select(hierarchy["slide_1"], _request(False))
        item_service.select(hierarchy["slide_2"], _request(False))
        assert _curator_excluded(sqlite_database_service, hierarchy) == {
            "slide_1",
            "slide_2",
        }

        # Act
        result = item_service.select(hierarchy["block"], _request(True))

        # Assert
        assert result is not None
        assert _names(hierarchy, result.kept_out) == {"slide_1", "slide_2"}
        selected = _selected(sqlite_database_service, hierarchy)
        assert "block" in selected
        assert not {"slide_1", "slide_2"} & selected
        assert "block" in _names(hierarchy, result.left_invalid)

    def test_what_a_cascade_would_bring_back_against_curation_is_reported(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """The case was taken out by name; a slide under it asks for it."""
        # Arrange
        item_service.select(hierarchy["case"], _request(False))

        # Act
        result = item_service.select(hierarchy["slide_1"], _request(True))

        # Assert
        assert result is not None
        assert _names(hierarchy, result.kept_out) == {"case"}
        assert "case" not in _selected(sqlite_database_service, hierarchy)
        assert {"specimen_1", "specimen_2"} <= _names(hierarchy, result.left_invalid)

    def test_overriding_curation_brings_it_back_and_clears_the_mark(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        item_service.select(hierarchy["case"], _request(False))

        # Act
        result = item_service.select(
            hierarchy["slide_1"], _request(True, override_curation=True)
        )

        # Assert
        assert result is not None
        overridden = [change for change in result.changed if change.overrode_curation]
        assert _names(hierarchy, overridden) == {"case"}
        assert {"case", "patient"} <= _selected(sqlite_database_service, hierarchy)
        assert _curator_excluded(sqlite_database_service, hierarchy) == set()

    def test_asking_for_an_item_by_name_clears_its_own_mark(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        item_service.select(hierarchy["slide_1"], _request(False))

        # Act
        item_service.select(hierarchy["slide_1"], _request(True))

        # Assert
        assert "slide_1" in _selected(sqlite_database_service, hierarchy)
        assert _curator_excluded(sqlite_database_service, hierarchy) == set()


@pytest.mark.unittest
class TestScope:
    def test_not_cascading_up_leaves_the_block_without_slides(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        item_service.select(hierarchy["slide_1"], _request(False))

        # Act
        result = item_service.select(
            hierarchy["slide_2"], _request(False, cascade_up=False)
        )

        # Assert
        assert result is not None
        selected = _selected(sqlite_database_service, hierarchy)
        assert "block" in selected
        assert "image_2" not in selected
        assert "block" in _names(hierarchy, result.left_invalid)

    def test_not_cascading_down_leaves_the_image_on_a_slide_that_is_out(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        result = item_service.select(
            hierarchy["slide_1"], _request(False, cascade_down=False)
        )

        # Assert
        assert result is not None
        assert "image_1" in _selected(sqlite_database_service, hierarchy)
        assert "image_1" in _names(hierarchy, result.left_invalid)

    def test_a_skipped_schema_is_left_as_it_is(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        item_service.select(
            hierarchy["image_1"], _request(False, skip_schemas=[Uids.annotation])
        )

        # Assert
        selected = _selected(sqlite_database_service, hierarchy)
        assert "annotation" in selected
        assert "note" not in selected

    def test_the_direction_each_change_was_reached_in_is_reported(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        result = item_service.select(hierarchy["image_2"], _request(False))

        # Assert
        assert result is not None
        directions = {
            name: change.direction
            for name, change in zip(
                [
                    {uid: name for name, uid in hierarchy.items()}[change.uid]
                    for change in result.changed
                ],
                result.changed,
                strict=True,
            )
        }
        assert directions == {
            "image_2": CascadeDirection.ITEM,
            "slide_2": CascadeDirection.UP,
        }


@pytest.mark.unittest
class TestDryRun:
    def test_a_dry_run_reports_what_the_request_would_do_and_changes_nothing(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        before = _selected(sqlite_database_service, hierarchy)

        # Act
        preview = item_service.select(
            hierarchy["slide_1"], _request(False, dry_run=True)
        )

        # Assert
        assert preview is not None
        assert preview.dry_run
        assert _selected(sqlite_database_service, hierarchy) == before
        assert _curator_excluded(sqlite_database_service, hierarchy) == set()
        applied = item_service.select(hierarchy["slide_1"], _request(False))
        assert applied is not None
        assert _names(hierarchy, preview.changed) == _names(hierarchy, applied.changed)


def _tree(item_service: ItemService, item_uid: UUID, select: bool) -> SelectionTree:
    trees = item_service.selection_trees([item_uid], select)
    assert trees is not None
    return trees[0]


def _bulk(item_uids: list[UUID], select: bool, items: list[UUID]) -> ItemBulkSelect:
    return ItemBulkSelect(item_uids=item_uids, select=select, items=items)


def _tree_names(
    hierarchy: dict[str, UUID], nodes: Iterable[SelectionTreeNode]
) -> dict[str, dict]:
    """The tree by name, each node as its children by name, with its flags."""
    by_uid = {uid: name for name, uid in hierarchy.items()}
    return {
        by_uid[node.uid]: {
            "default": node.default,
            "selectable": node.selectable,
            "children": _tree_names(hierarchy, node.children),
        }
        for node in nodes
    }


def _defaults(nodes: Iterable[SelectionTreeNode]) -> set[UUID]:
    found: set[UUID] = set()
    for node in nodes:
        if node.default:
            found.add(node.uid)
            found |= {with_it.uid for with_it in node.with_it}
        found |= _defaults(node.children)
    return found


@pytest.mark.unittest
class TestSelectionTree:
    def test_taking_a_case_out_offers_its_patient_and_everything_below_it(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        tree = _tree(item_service, hierarchy["case"], False)

        # Assert
        assert tree is not None
        assert _tree_names(hierarchy, tree.up) == {
            "patient": {"default": True, "selectable": True, "children": {}}
        }
        down = _tree_names(hierarchy, tree.down)
        assert set(down) == {"diagnosis", "specimen_1", "specimen_2"}
        block = down["specimen_1"]["children"]["block"]
        assert block == down["specimen_2"]["children"]["block"]
        assert set(block["children"]) == {"macro", "slide_1", "slide_2"}
        assert set(block["children"]["slide_1"]["children"]) == {"image_1"}

    def test_a_patient_with_another_case_is_shown_but_not_offered(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
    ):
        """Taking the patient out would take the other case with it."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            patient = sqlite_database_service.get_sample(session, hierarchy["patient"])
            session.add(
                DatabaseSample(
                    dataset.uid, batch_uid, Uids.case, "other_case", parents=patient
                )
            )
            session.commit()

        # Act
        tree = _tree(item_service, hierarchy["case"], False)

        # Assert
        assert tree is not None
        assert _tree_names(hierarchy, tree.up) == {
            "patient": {"default": False, "selectable": False, "children": {}}
        }

    def test_nothing_changes_while_the_tree_is_worked_out(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        before = _selected(sqlite_database_service, hierarchy)

        # Act
        _tree(item_service, hierarchy["case"], False)

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == before
        assert _curator_excluded(sqlite_database_service, hierarchy) == set()

    def test_choosing_every_default_does_what_the_cascade_does(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        tree = _tree(item_service, hierarchy["case"], False)
        assert tree is not None
        chosen = _defaults(tree.up) | _defaults(tree.down)

        # Act
        item_service.select_many(
            _bulk([hierarchy["case"]], False, sorted(chosen, key=str))
        )

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == set()

    def test_stopping_at_the_specimens_leaves_what_is_below_them(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """What the curator did not choose stays in, and is marked as not
        valid for having nothing left to belong to."""
        # Arrange
        chosen = [hierarchy[name] for name in ("diagnosis", "specimen_1", "specimen_2")]

        # Act
        result = item_service.select_many(_bulk([hierarchy["case"]], False, chosen))

        # Assert
        assert result is not None
        selected = _selected(sqlite_database_service, hierarchy)
        assert {"patient", "block", "slide_1", "slide_2"} <= selected
        assert not {"case", "diagnosis", "specimen_1", "specimen_2"} & selected
        assert "block" in _names(hierarchy, result.left_invalid)
        assert _curator_excluded(sqlite_database_service, hierarchy) == {"case"}

    def test_restoring_shows_what_was_removed_by_hand_as_not_chosen(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        item_service.select(hierarchy["slide_1"], _request(False))
        item_service.select(hierarchy["block"], _request(False))

        # Act
        tree = _tree(item_service, hierarchy["block"], True)

        # Assert
        assert tree is not None
        down = {node.uid: node for node in tree.down}
        slide_1 = down[hierarchy["slide_1"]]
        assert slide_1.curator_excluded
        assert not slide_1.default
        assert slide_1.selectable
        assert down[hierarchy["slide_2"]].default

    def test_choosing_something_removed_by_hand_brings_it_back(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        item_service.select(hierarchy["slide_1"], _request(False))
        item_service.select(hierarchy["block"], _request(False))

        # Act
        result = item_service.select_many(
            _bulk(
                [hierarchy["block"]], True, [hierarchy["slide_1"], hierarchy["image_1"]]
            )
        )

        # Assert
        assert result is not None
        assert {"slide_1", "image_1"} <= _selected(sqlite_database_service, hierarchy)
        overridden = [change for change in result.changed if change.overrode_curation]
        assert _names(hierarchy, overridden) == {"slide_1"}

    def test_items_taken_together_offer_what_none_would_alone(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """One slide leaves the block its other slide; both leave it nothing,
        so the block and everything above it are offered, and the other slide
        is not a choice in the first one's tree since it was asked for."""
        # Arrange
        slides = [hierarchy["slide_1"], hierarchy["slide_2"]]

        # Act
        trees = item_service.selection_trees(slides, False)

        # Assert
        assert trees is not None
        first_up = _tree_names(hierarchy, trees[0].up)
        assert first_up["block"]["default"]
        assert first_up["block"]["selectable"]
        for tree in trees:
            assert not {"slide_1", "slide_2"} & set(_tree_names(hierarchy, tree.down))
        single = _tree(item_service, hierarchy["slide_1"], False)
        assert not _tree_names(hierarchy, single.up)["block"]["selectable"]

    def test_choosing_every_default_for_several_does_what_the_cascade_does(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        slides = [hierarchy["slide_1"], hierarchy["slide_2"]]
        trees = item_service.selection_trees(slides, False)
        assert trees is not None
        chosen: set[UUID] = set()
        for tree in trees:
            chosen |= _defaults(tree.up) | _defaults(tree.down)

        # Act
        result = item_service.select_many(_bulk(slides, False, sorted(chosen, key=str)))

        # Assert
        assert result is not None
        assert _selected(sqlite_database_service, hierarchy) == set()
        assert _curator_excluded(sqlite_database_service, hierarchy) == {
            "slide_1",
            "slide_2",
        }

    def test_a_bulk_dry_run_changes_nothing(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        before = _selected(sqlite_database_service, hierarchy)

        # Act
        preview = item_service.select_many(
            ItemBulkSelect(
                item_uids=[hierarchy["slide_1"], hierarchy["slide_2"]],
                select=False,
                dry_run=True,
            )
        )

        # Assert
        assert preview is not None
        assert "block" in _names(hierarchy, preview.left_invalid)
        assert _selected(sqlite_database_service, hierarchy) == before


@pytest.mark.unittest
class TestShortcuts:
    """A specimen related to its patient both directly and through its case,
    as the BigPicture schema relates a specimen to its being."""

    @pytest.fixture()
    def hierarchy(
        self,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ) -> dict[str, UUID]:
        with sqlite_database_service.get_session() as session:
            specimen = sqlite_database_service.get_sample(
                session, hierarchy["specimen_1"]
            )
            patient = sqlite_database_service.get_sample(session, hierarchy["patient"])
            specimen.parents.add(patient)
            session.commit()
        return hierarchy

    def test_the_specimen_is_shown_under_its_case_and_not_again_directly(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        tree = _tree(item_service, hierarchy["patient"], False)

        # Assert
        down = _tree_names(hierarchy, tree.down)
        assert set(down) == {"case"}
        assert "specimen_1" in down["case"]["children"]

    def test_the_patient_is_shown_above_the_case_and_not_again_directly(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        tree = _tree(item_service, hierarchy["specimen_1"], False)

        # Assert
        up = _tree_names(hierarchy, tree.up)
        assert set(up) == {"case"}
        assert set(up["case"]["children"]) == {"patient"}

    def test_a_block_from_two_specimens_is_still_shown_under_both(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        """Neither specimen is on the way to the other, so neither relation
        is a shortcut."""
        # Arrange

        # Act
        tree = _tree(item_service, hierarchy["case"], False)

        # Assert
        down = _tree_names(hierarchy, tree.down)
        assert "block" in down["specimen_1"]["children"]
        assert "block" in down["specimen_2"]["children"]


@pytest.mark.unittest
class TestBulkSelectGuards:
    """What a request to select or deselect with chosen items is held to."""

    @pytest.fixture()
    def review_service(self, decoy: Decoy) -> ReviewService:
        return decoy.mock(cls=ReviewService)

    @pytest.fixture()
    def item_service(
        self,
        sqlite_database_service: DatabaseService,
        schema: RootSchema,
        validation_service: ValidationService,
        review_service: ReviewService,
    ) -> ItemService:
        """The item service with the review service watched, to see what it
        is told."""
        schema_service = SchemaService(schema)
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
    def hierarchy(
        self,
        sqlite_database_service: DatabaseService,
        validation_service: ValidationService,
        hierarchy: dict[str, UUID],
    ) -> dict[str, UUID]:
        """Everything valid to begin with, so what a change leaves not valid
        is a crossing the review has to hear about."""
        with sqlite_database_service.get_session() as session:
            for uid in hierarchy.values():
                sqlite_database_service.get_item(session, uid).valid_attributes = True
            validation_service.validate_relations_for(hierarchy.values(), session)
            session.commit()
        return hierarchy

    def test_a_case_left_without_specimens_is_reported_as_no_longer_valid(
        self,
        decoy: Decoy,
        item_service: ItemService,
        review_service: ReviewService,
        hierarchy: dict[str, UUID],
    ):
        """The curator takes out both specimens and keeps the case. The case
        did not change, but it now needs a specimen it does not have."""
        # Arrange
        specimens = [hierarchy["specimen_1"], hierarchy["specimen_2"]]

        # Act
        item_service.select_many(_bulk(specimens, False, []))

        # Assert
        decoy.verify(
            review_service.item_validity_changed(
                hierarchy["case"],
                was_valid=True,
                is_valid=False,
                session=matchers.Anything(),
            )
        )

    def test_an_unknown_chosen_item_is_not_found(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange
        before = _selected(sqlite_database_service, hierarchy)

        # Act
        result = item_service.select_many(_bulk([hierarchy["case"]], False, [uuid4()]))

        # Assert
        assert result is None
        assert _selected(sqlite_database_service, hierarchy) == before

    def test_an_item_from_another_hierarchy_is_refused(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            other = DatabaseSample(dataset.uid, batch_uid, Uids.patient, "other")
            session.add(other)
            session.commit()
            other_uid = other.uid
        before = _selected(sqlite_database_service, hierarchy)

        # Act
        with pytest.raises(NotAllowedActionError):
            item_service.select_many(_bulk([hierarchy["case"]], False, [other_uid]))

        # Assert
        assert _selected(sqlite_database_service, hierarchy) == before
        with sqlite_database_service.get_session() as session:
            assert sqlite_database_service.get_item(session, other_uid).selected
