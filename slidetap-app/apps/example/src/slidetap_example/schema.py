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

"""Example schema."""

from typing import Type
from uuid import UUID

from slidetap.external_interfaces.schema import SchemaInterface
from slidetap.model import (
    CodeAttributeSchema,
    DatasetSchema,
    EnumAttributeSchema,
    ImageSchema,
    ImageToSampleRelation,
    ListAttributeSchema,
    ObservationSchema,
    ObservationToSampleRelation,
    ProjectSchema,
    RootSchema,
    SampleSchema,
    SampleToSampleRelation,
    StringAttributeSchema,
)


class ExampleSchema(RootSchema):
    def __init__(self) -> None:
        project_schema = ProjectSchema(
            uid=UUID("ab2fa0af-4e43-4446-a357-aeab826f5487"),
            name="Project",
            display_name="Project",
            attributes={
                "submitter": StringAttributeSchema(
                    uid=UUID("e1078f88-6c5b-4fed-8323-0203235b89f5"),
                    name="submitter",
                    tag="submitter",
                    display_name="Submitter",
                    optional=False,
                    read_only=False,
                    display_in_table=True,
                )
            },
        )
        dataset_schema = DatasetSchema(
            uid=UUID("19fb4363-783a-48e9-9757-4be1c6204300"),
            name="Dataset",
            display_name="Dataset",
            attributes={},
        )
        super().__init__(
            uid=UUID("752ee40c-5ebe-48cf-b384-7001239ee70d"),
            name="Example schema",
            project=project_schema,
            dataset=dataset_schema,
            images={self.image.uid: self.image},
            samples={
                self.slide.uid: self.slide,
                self.block.uid: self.block,
                self.specimen.uid: self.specimen,
                self.case.uid: self.case,
                self.patient.uid: self.patient,
            },
            observations={self.observation.uid: self.observation},
        )

    @property
    def slide_schema_uid(self) -> UUID:
        return UUID("9540df72-8fb5-49f2-a487-52308837cc82")

    @property
    def block_schema_uid(self) -> UUID:
        return UUID("049693a1-427c-4954-836d-04171fdbcf40")

    @property
    def specimen_schema_uid(self) -> UUID:
        return UUID("c78d0dcf-1723-4729-8c05-d438a184c6b4")

    @property
    def case_schema_uid(self) -> UUID:
        return UUID("26811402-e1e7-45eb-bc13-848295227930")

    @property
    def patient_schema_uid(self) -> UUID:
        return UUID("d392e448-3827-4244-b1f4-0b8c685082cc")

    @property
    def image_schema_uid(self) -> UUID:
        return UUID("7fd921e7-59fc-46b0-8b9f-eaf6c293ca22")

    @property
    def observation_schema_uid(self) -> UUID:
        return UUID("7158078e-a02a-4dd3-a13d-3de3eb16fd7a")

    @property
    def slide_to_image_relation(self) -> ImageToSampleRelation:
        return ImageToSampleRelation(
            uid=UUID("d577f377-f43f-4bd4-9bf8-6ee75f640a53"),
            name="Image of slide",
            description=None,
            image_uid=self.image_schema_uid,
            sample_uid=self.slide_schema_uid,
            image_title="WSI",
            sample_title="Slide",
        )

    @property
    def block_to_slide_relation(self) -> SampleToSampleRelation:
        return SampleToSampleRelation(
            uid=UUID("d4b0ebaf-3a41-41ba-8704-33067a3e374e"),
            name="Sampling to slide",
            description=None,
            parent_uid=self.block_schema_uid,
            child_uid=self.slide_schema_uid,
            min_parents=1,
            max_parents=1,
            min_children=1,
            max_children=None,
            parent_title="Block",
            child_title="Slides",
        )

    @property
    def specimen_to_block_relation(self) -> SampleToSampleRelation:
        return SampleToSampleRelation(
            uid=UUID("67b90098-84ce-4005-b82f-9d4e03513af5"),
            name="Sampling to block",
            description=None,
            parent_uid=self.specimen_schema_uid,
            child_uid=self.block_schema_uid,
            min_parents=1,
            max_parents=None,
            min_children=1,
            max_children=None,
            parent_title="Specimens",
            child_title="Blocks",
        )

    @property
    def case_to_specimen_relation(self) -> SampleToSampleRelation:
        return SampleToSampleRelation(
            uid=UUID("b2a0f8fd-093f-4d46-bc37-052ddcc6f0ca"),
            name="Case to specimen",
            description=None,
            parent_uid=self.case_schema_uid,
            child_uid=self.specimen_schema_uid,
            min_parents=1,
            max_parents=1,
            min_children=1,
            max_children=None,
            parent_title="Case",
            child_title="Specimens",
        )

    @property
    def patient_to_case_relation(self) -> SampleToSampleRelation:
        return SampleToSampleRelation(
            uid=UUID("9e4409b1-3a4f-4488-8f72-2a30af392bb9"),
            name="Patient to case",
            description=None,
            parent_uid=self.patient_schema_uid,
            child_uid=self.case_schema_uid,
            min_parents=1,
            max_parents=1,
            min_children=1,
            max_children=None,
            parent_title="Patient",
            child_title="Cases",
        )

    @property
    def observation_to_case_relation(self) -> ObservationToSampleRelation:
        return ObservationToSampleRelation(
            uid=UUID("7fd921e7-59fc-46b0-8b9f-eaf6c293ca22"),
            name="Observation to case",
            description=None,
            observation_uid=self.observation_schema_uid,
            sample_uid=self.case_schema_uid,
            observation_title="Observation",
            sample_title="Case",
        )

    @property
    def patient(self) -> SampleSchema:
        return SampleSchema(
            uid=self.patient_schema_uid,
            name="patient",
            display_name="Patient",
            display_order=0,
            attributes={
                "sex": EnumAttributeSchema(
                    uid=UUID("1eac6f2a-6395-4da9-b606-e364938b6da2"),
                    tag="sex",
                    name="sex",
                    display_name="Sex",
                    optional=False,
                    read_only=False,
                    display_in_table=True,
                    allowed_values=("M", "F", "Other", "Unknown"),
                )
            },
            children=(self.patient_to_case_relation,),
            parents=(),
            images=(),
            observations=(),
        )

    @property
    def case(self) -> SampleSchema:
        return SampleSchema(
            uid=self.case_schema_uid,
            name="case",
            display_name="Case",
            display_order=1,
            attributes={},
            children=(self.case_to_specimen_relation,),
            parents=(self.patient_to_case_relation,),
            images=(),
            observations=(self.observation_to_case_relation,),
        )

    @property
    def block(self) -> SampleSchema:
        return SampleSchema(
            uid=self.block_schema_uid,
            name="block",
            display_name="Block",
            display_order=3,
            attributes={
                "embedding": CodeAttributeSchema(
                    uid=UUID("64f8ab56-1748-49c0-a03d-21dfe4094e75"),
                    tag="embedding",
                    name="embedding",
                    display_name="Embedding",
                    optional=False,
                    read_only=False,
                    display_in_table=True,
                ),
                "block_sampling": CodeAttributeSchema(
                    uid=UUID("1a127772-48f8-4330-9fb6-30ceeecfba02"),
                    tag="block_sampling",
                    name="block_sampling",
                    display_name="Sampling method",
                    optional=False,
                    read_only=False,
                    display_in_table=True,
                ),
            },
            children=(self.block_to_slide_relation,),
            parents=(self.specimen_to_block_relation,),
            images=(),
            observations=(),
        )

    @property
    def slide(self) -> SampleSchema:
        return SampleSchema(
            uid=self.slide_schema_uid,
            name="slide",
            display_name="Slide",
            display_order=4,
            attributes={
                "staining": ListAttributeSchema(
                    uid=UUID("254a5ff4-faf2-412d-9967-31d652592d2a"),
                    tag="staining",
                    name="staining",
                    display_name="Staining",
                    optional=False,
                    read_only=False,
                    display_in_table=True,
                    display_attributes_in_parent=True,
                    attribute=CodeAttributeSchema(
                        uid=UUID("5d8ebb2f-44db-4fc4-bee5-8402a6c6d38e"),
                        tag="stain",
                        name="stain",
                        display_name="Stain",
                        optional=False,
                        read_only=False,
                        display_in_table=True,
                    ),
                )
            },
            children=(),
            parents=(self.block_to_slide_relation,),
            images=(self.slide_to_image_relation,),
            observations=(),
        )

    @property
    def specimen(self) -> SampleSchema:
        return SampleSchema(
            uid=self.specimen_schema_uid,
            name="specimen",
            display_name="Specimen",
            display_order=2,
            attributes={
                "fixation": CodeAttributeSchema(
                    uid=UUID("8173e06c-de74-46a0-a517-1161c642746d"),
                    tag="fixation",
                    name="fixation",
                    display_name="Fixation",
                    optional=False,
                    read_only=False,
                    display_in_table=True,
                ),
                "collection": CodeAttributeSchema(
                    uid=UUID("5d2d0787-8d1f-4f79-82d9-44f2cab4ecd7"),
                    tag="collection",
                    name="collection",
                    display_name="Collection method",
                    optional=False,
                    read_only=False,
                    display_in_table=True,
                ),
            },
            children=(self.specimen_to_block_relation,),
            parents=(self.case_to_specimen_relation,),
            images=(),
        )

    @property
    def image(self) -> ImageSchema:
        return ImageSchema(
            uid=self.image_schema_uid,
            name="wsi",
            display_name="WSI",
            display_order=5,
            attributes={},
            samples=(self.slide_to_image_relation,),
            observations=(),
            annotations=(),
        )

    @property
    def observation(self) -> ObservationSchema:
        return ObservationSchema(
            uid=self.observation_schema_uid,
            name="observation",
            display_name="Observation",
            display_order=6,
            attributes={
                "diagnose": StringAttributeSchema(
                    uid=UUID("c3d4e5f6-a7b8-9c0d-e1f2-a3b4c5d6e7f8"),
                    tag="diagnose",
                    name="diagnose",
                    display_name="Diagnose",
                    optional=False,
                    read_only=False,
                    display_in_table=True,
                )
            },
            private_attributes={
                "report": StringAttributeSchema(
                    uid=UUID("36181df6-4edf-41ce-a625-c2b63264eebc"),
                    tag="report",
                    name="report",
                    display_name="Report",
                    optional=True,
                    read_only=True,
                    display_in_table=False,
                    multiline=True,
                )
            },
            samples=(self.observation_to_case_relation,),
        )


class ExampleSchemaInterface(SchemaInterface):
    def create(self) -> RootSchema:
        return ExampleSchema()

    @classmethod
    def get_schema_type(cls) -> Type[RootSchema]:
        return ExampleSchema
