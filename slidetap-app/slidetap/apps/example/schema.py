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

from uuid import UUID

from slidetap.model import (
    CodeAttributeSchema,
    DatasetSchema,
    ImageSchema,
    ImageToSampleRelation,
    ListAttributeSchema,
    RootSchema,
    SampleSchema,
    SampleToSampleRelation,
    StringAttributeSchema,
)
from slidetap.model.schema.project_schema import ProjectSchema


class ExampleSchema(RootSchema):
    def __init__(self):
        self._slide_schema_uid = UUID("9540df72-8fb5-49f2-a487-52308837cc82")
        self._block_schema_uid = UUID("049693a1-427c-4954-836d-04171fdbcf40")
        self._specimen_schema_uid = UUID("c78d0dcf-1723-4729-8c05-d438a184c6b4")
        self._image_schema_uid = UUID("f537cbcc-8d71-4874-a900-3e6d2a377728")
        slide_to_image_relation = ImageToSampleRelation(
            uid=UUID("d577f377-f43f-4bd4-9bf8-6ee75f640a53"),
            name="Image of slide",
            description=None,
            image_uid=self._image_schema_uid,
            sample_uid=self._slide_schema_uid,
            image_title="WSI",
            sample_title="Slide",
        )
        block_to_slide_relation = SampleToSampleRelation(
            uid=UUID("d4b0ebaf-3a41-41ba-8704-33067a3e374e"),
            name="Sampling to slide",
            description=None,
            parent_uid=self._block_schema_uid,
            child_uid=self._slide_schema_uid,
            min_parents=1,
            max_parents=1,
            min_children=1,
            max_children=None,
            parent_title="Block",
            child_title="Slides",
        )
        specimen_to_block_relation = SampleToSampleRelation(
            uid=UUID("67b90098-84ce-4005-b82f-9d4e03513af5"),
            name="Sampling to block",
            description=None,
            parent_uid=self._specimen_schema_uid,
            child_uid=self._block_schema_uid,
            min_parents=1,
            max_parents=None,
            min_children=1,
            max_children=None,
            parent_title="Specimens",
            child_title="Blocks",
        )

        image = ImageSchema(
            uid=self._image_schema_uid,
            name="wsi",
            display_name="WSI",
            display_order=3,
            attributes={},
            samples=(slide_to_image_relation,),
            observations=(),
            annotations=(),
        )
        slide = SampleSchema(
            uid=self._slide_schema_uid,
            name="slide",
            display_name="Slide",
            display_order=2,
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
            parents=(block_to_slide_relation,),
            images=(slide_to_image_relation,),
            observations=(),
        )
        block = SampleSchema(
            uid=self._block_schema_uid,
            name="block",
            display_name="Block",
            display_order=1,
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
            children=(block_to_slide_relation,),
            parents=(specimen_to_block_relation,),
            images=(),
            observations=(),
        )
        specimen = SampleSchema(
            uid=self._specimen_schema_uid,
            name="specimen",
            display_name="Specimen",
            display_order=0,
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
            children=(specimen_to_block_relation,),
            parents=(),
            images=(),
            observations=(),
        )

        project = ProjectSchema(
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
        dataset = DatasetSchema(
            uid=UUID("19fb4363-783a-48e9-9757-4be1c6204300"),
            name="Dataset",
            display_name="Dataset",
            attributes={},
        )

        super().__init__(
            uid=UUID("752ee40c-5ebe-48cf-b384-7001239ee70d"),
            name="Example schema",
            project=project,
            dataset=dataset,
            samples={slide.uid: slide, block.uid: block, specimen.uid: specimen},
            images={image.uid: image},
            annotations={},
            observations={},
        )

    @property
    def block(self) -> SampleSchema:
        return self.samples[self._block_schema_uid]

    @property
    def slide(self) -> SampleSchema:
        return self.samples[self._slide_schema_uid]

    @property
    def specimen(self) -> SampleSchema:
        return self.samples[self._specimen_schema_uid]

    @property
    def image(self) -> ImageSchema:
        return self.images[self._image_schema_uid]
