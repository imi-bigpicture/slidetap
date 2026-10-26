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

"""Tests for making a sample for a parked image from the tree.

The schema is a case of specimens of blocks of slides, with an image of a
slide that is parked on the case where it matches no slide. The image keeps
what it was filed under elsewhere as a private stain, which the slide made for
it is given to map.
"""

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest

from slidetap.database import (
    DatabaseImage,
    DatabaseSample,
    DatabaseStringAttribute,
)
from slidetap.model import (
    Cardinality,
    Dataset,
    HierarchyLayout,
    HierarchyLevelLayout,
    ImageFormat,
    NotAllowedActionError,
    Project,
    SampleForImageLayout,
    StringAttributeSchema,
)
from slidetap.model.batch import BatchCreate
from slidetap.model.schema.dataset_schema import DatasetSchema
from slidetap.model.schema.item_relation import (
    ImageToSampleRelation,
    SampleToSampleRelation,
)
from slidetap.model.schema.item_schema import ImageSchema, SampleSchema
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

    case = uuid4()
    specimen = uuid4()
    block = uuid4()
    slide = uuid4()
    image = uuid4()
    layout = uuid4()
    other_layout = uuid4()


STAINING = StringAttributeSchema(
    uid=uuid4(),
    tag="staining",
    name="staining",
    display_name="Staining",
    optional=False,
    read_only=False,
)
PACS_STAINING = StringAttributeSchema(
    uid=uuid4(),
    tag="pacs_staining",
    name="pacs_staining",
    display_name="PACS staining",
    optional=True,
    read_only=True,
)


@pytest.fixture()
def schema() -> RootSchema:
    def sample_to_sample(parent: UUID, child: UUID) -> SampleToSampleRelation:
        return SampleToSampleRelation(
            uid=uuid4(),
            name=f"{parent} to {child}",
            parent_uid=parent,
            child_uid=child,
            parents=Cardinality.ONE,
            children=Cardinality.ONE_OR_MORE,
            parent_title="Parent",
            child_title="Child",
        )

    case_to_specimen = sample_to_sample(Uids.case, Uids.specimen)
    specimen_to_block = sample_to_sample(Uids.specimen, Uids.block)
    block_to_slide = sample_to_sample(Uids.block, Uids.slide)
    slide_to_image = ImageToSampleRelation(
        uid=uuid4(),
        name="Image of slide",
        image_uid=Uids.image,
        sample_uid=Uids.slide,
        samples=Cardinality.ONE,
        image_title="WSI",
        sample_title="Slide",
    )
    parked_on_case = ImageToSampleRelation(
        uid=uuid4(),
        name="Image parked on case",
        image_uid=Uids.image,
        sample_uid=Uids.case,
        images=Cardinality.ZERO_OR_MORE,
        image_title="WSI",
        sample_title="Case",
        orphan=True,
    )

    def sample(uid: UUID, name: str, order: int, **kwargs) -> SampleSchema:
        return SampleSchema(
            uid=uid, name=name, display_name=name.title(), display_order=order, **kwargs
        )

    image_level = HierarchyLevelLayout(
        schema_uid=Uids.image,
        inline=True,
        movable=True,
        sample_for_image=SampleForImageLayout(
            sample_schema_uid=Uids.slide,
            parent_schema_uid=Uids.block,
            mappable_values={STAINING.tag: PACS_STAINING.tag},
        ),
    )
    return RootSchema(
        uid=uuid4(),
        name="Sample for image",
        project=ProjectSchema(
            uid=uuid4(), name="project", display_name="Project", attributes={}
        ),
        dataset=DatasetSchema(
            uid=uuid4(), name="dataset", display_name="Dataset", attributes={}
        ),
        samples={
            Uids.case: sample(
                Uids.case,
                "case",
                0,
                children=(case_to_specimen,),
                images=(parked_on_case,),
            ),
            Uids.specimen: sample(
                Uids.specimen,
                "specimen",
                1,
                children=(specimen_to_block,),
                parents=(case_to_specimen,),
            ),
            Uids.block: sample(
                Uids.block,
                "block",
                2,
                children=(block_to_slide,),
                parents=(specimen_to_block,),
            ),
            Uids.slide: sample(
                Uids.slide,
                "slide",
                3,
                parents=(block_to_slide,),
                images=(slide_to_image,),
                attributes={STAINING.tag: STAINING},
            ),
        },
        images={
            Uids.image: ImageSchema(
                uid=Uids.image,
                name="wsi",
                display_name="WSI",
                display_order=4,
                samples=(slide_to_image, parked_on_case),
                private_attributes={PACS_STAINING.tag: PACS_STAINING},
            ),
        },
        hierarchy_layouts=[
            HierarchyLayout(
                uid=Uids.layout,
                name="lab",
                display_name="Lab",
                schema_uid=Uids.case,
                levels=[
                    HierarchyLevelLayout(schema_uid=Uids.specimen),
                    HierarchyLevelLayout(schema_uid=Uids.block),
                    HierarchyLevelLayout(schema_uid=Uids.slide),
                    image_level,
                ],
            ),
            # The same tree without the offer to make a slide.
            HierarchyLayout(
                uid=Uids.other_layout,
                name="plain",
                display_name="Plain",
                schema_uid=Uids.case,
                levels=[
                    HierarchyLevelLayout(schema_uid=Uids.block),
                    HierarchyLevelLayout(schema_uid=Uids.image, movable=True),
                ],
            ),
        ],
    )


@pytest.fixture()
def batch_uid(
    stored_database_service: DatabaseService, dataset: Dataset, project: Project
) -> UUID:
    with stored_database_service.get_session() as session:
        stored_database_service.add_dataset(session, dataset)
        stored_database_service.add_project(session, project)
        return stored_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        ).uid


@pytest.fixture()
def item_service(
    stored_database_service: DatabaseService,
    schema: RootSchema,
    schema_service_of: Callable[..., SchemaService],
) -> ItemService:
    schema_service = schema_service_of(schema)
    validation_service = ValidationService(schema_service, stored_database_service)
    review_service = ReviewService(
        schema_service, validation_service, stored_database_service
    )
    attribute_service = AttributeService(
        schema_service, validation_service, stored_database_service, review_service
    )
    return ItemService(
        attribute_service,
        TagService(stored_database_service),
        MapperService(
            attribute_service,
            validation_service,
            schema_service,
            stored_database_service,
            review_service,
        ),
        schema_service,
        validation_service,
        stored_database_service,
        review_service,
    )


@pytest.fixture()
def hierarchy(
    stored_database_service: DatabaseService, dataset: Dataset, batch_uid: UUID
) -> dict[str, UUID]:
    """Two cases, as the uid of each item by name.

    case_1
      specimen_1
        block_1
          slide_1 (image_on_slide)
      parked: image "PL-1-3", which PACS has stained "HE"
    case_2
      specimen_2
        block_2
    """

    def sample(schema_uid: UUID, name: str, **kwargs) -> DatabaseSample:
        return DatabaseSample(dataset.uid, batch_uid, schema_uid, name, **kwargs)

    def image(name: str, on: DatabaseSample, **kwargs) -> DatabaseImage:
        return DatabaseImage(
            dataset.uid,
            batch_uid,
            Uids.image,
            name,
            ImageFormat.OTHER_WSI,
            samples=on,
            **kwargs,
        )

    with stored_database_service.get_session() as session:
        case_1 = sample(Uids.case, "case_1")
        specimen_1 = sample(Uids.specimen, "specimen_1", parents=case_1)
        block_1 = sample(Uids.block, "block_1", parents=specimen_1)
        slide_1 = sample(Uids.slide, "slide_1", parents=block_1)
        image_on_slide = image("image_on_slide", slide_1)
        parked = image(
            "PL-1-3",
            case_1,
            private_attributes=[
                DatabaseStringAttribute(
                    tag=PACS_STAINING.tag,
                    schema_uid=PACS_STAINING.uid,
                    original_value="HE",
                    display_value="HE",
                    valid=True,
                )
            ],
        )
        case_2 = sample(Uids.case, "case_2")
        specimen_2 = sample(Uids.specimen, "specimen_2", parents=case_2)
        block_2 = sample(Uids.block, "block_2", parents=specimen_2)
        session.add_all([case_1, case_2])
        session.commit()
        return {
            "case_1": case_1.uid,
            "block_1": block_1.uid,
            "slide_1": slide_1.uid,
            "image_on_slide": image_on_slide.uid,
            "parked": parked.uid,
            "block_2": block_2.uid,
        }


@pytest.mark.unittest
class TestSampleForImage:
    def test_the_image_is_put_on_a_new_slide_under_the_block(
        self,
        item_service: ItemService,
        stored_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        slide = item_service.create_sample_for_image(
            hierarchy["parked"], Uids.layout, hierarchy["block_1"]
        )

        # Assert
        with stored_database_service.get_session() as session:
            stored = stored_database_service.get_item(session, slide.uid)
            image = stored_database_service.get_item(session, hierarchy["parked"])
            assert isinstance(stored, DatabaseSample)
            assert isinstance(image, DatabaseImage)
            assert stored.schema_uid == Uids.slide
            assert stored.identifier == "PL-1-3"
            assert {parent.uid for parent in stored.parents} == {hierarchy["block_1"]}
            assert {sample.uid for sample in image.samples} == {slide.uid}

    def test_the_slide_is_given_the_stain_pacs_has_for_mapping(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        """As a mappable value, so it is mapped the way the stain an import
        left on a slide is, rather than taken as the stain itself."""
        # Arrange

        # Act
        slide = item_service.create_sample_for_image(
            hierarchy["parked"], Uids.layout, hierarchy["block_1"]
        )

        # Assert
        assert slide.attributes[STAINING.tag].mappable_value == "HE"

    def test_a_given_identifier_and_stain_are_used_instead(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        slide = item_service.create_sample_for_image(
            hierarchy["parked"],
            Uids.layout,
            hierarchy["block_1"],
            identifier="PL-1-4",
            mappable_values={STAINING.tag: "PAS"},
        )

        # Assert
        assert slide.identifier == "PL-1-4"
        assert slide.attributes[STAINING.tag].mappable_value == "PAS"

    def test_an_identifier_that_is_taken_is_refused(
        self,
        item_service: ItemService,
        stored_database_service: DatabaseService,
        hierarchy: dict[str, UUID],
    ):
        """Adding under a taken identifier hands back the slide that has it,
        which would put the image on a slide the laboratory registered."""
        # Arrange

        # Act
        with pytest.raises(NotAllowedActionError):
            item_service.create_sample_for_image(
                hierarchy["parked"],
                Uids.layout,
                hierarchy["block_1"],
                identifier="slide_1",
            )

        # Assert
        with stored_database_service.get_session() as session:
            image = stored_database_service.get_item(session, hierarchy["parked"])
            assert isinstance(image, DatabaseImage)
            assert {sample.uid for sample in image.samples} == {hierarchy["case_1"]}

    def test_an_image_on_a_slide_is_refused(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        with pytest.raises(NotAllowedActionError):
            item_service.create_sample_for_image(
                hierarchy["image_on_slide"],
                Uids.layout,
                hierarchy["block_1"],
                identifier="new",
            )

        # Assert

    def test_a_block_of_another_case_is_refused(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        with pytest.raises(ValueError):
            item_service.create_sample_for_image(
                hierarchy["parked"], Uids.layout, hierarchy["block_2"]
            )

        # Assert

    def test_a_parent_that_is_not_a_block_is_refused(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        with pytest.raises(ValueError):
            item_service.create_sample_for_image(
                hierarchy["parked"], Uids.layout, hierarchy["slide_1"]
            )

        # Assert

    def test_a_layout_without_the_offer_is_refused(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        with pytest.raises(NotAllowedActionError):
            item_service.create_sample_for_image(
                hierarchy["parked"], Uids.other_layout, hierarchy["block_1"]
            )

        # Assert

    def test_a_value_for_an_attribute_the_layout_does_not_fill_is_refused(
        self,
        item_service: ItemService,
        hierarchy: dict[str, UUID],
    ):
        # Arrange

        # Act
        with pytest.raises(ValueError):
            item_service.create_sample_for_image(
                hierarchy["parked"],
                Uids.layout,
                hierarchy["block_1"],
                mappable_values={"other": "value"},
            )

        # Assert
