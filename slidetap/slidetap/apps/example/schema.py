"""Example schema."""

from uuid import UUID

from slidetap.database.schema import ImageSchema, SampleSchema, Schema
from slidetap.database.schema.attribute_schema import (
    CodeAttributeSchema,
    ListAttributeSchema,
    StringAttributeSchema,
)
from slidetap.database.schema.item_schema import (
    ImageRelationDefinition,
    SampleRelationDefinition,
)
from slidetap.database.schema.project_schema import ProjectSchema


class ExampleSchema:
    uid = UUID("752ee40c-5ebe-48cf-b384-7001239ee70d")

    @classmethod
    def create(cls) -> Schema:
        schema = Schema.get_or_create(cls.uid, "Example schema")
        stain = CodeAttributeSchema.get_or_create(schema, "stain", "Stain")
        staining = ListAttributeSchema.get_or_create(
            schema, "staining", "Staining", stain
        )

        slide = SampleSchema.get_or_create(schema, "slide", "Slide", 2, [], [staining])
        sampling_method = CodeAttributeSchema.get_or_create(
            schema, "block_sampling", "Sampling method"
        )
        embedding = CodeAttributeSchema.get_or_create(schema, "embedding", "Embedding")

        block = SampleSchema.get_or_create(
            schema,
            "block",
            "Block",
            1,
            [SampleRelationDefinition("Sampling to slide", slide, 1, 1, 1, None)],
            [embedding, sampling_method],
        )

        fixation = CodeAttributeSchema.get_or_create(schema, "fixation", "Fixation")
        collection = CodeAttributeSchema.get_or_create(
            schema, "collection", "Collection method"
        )
        specimen = SampleSchema.get_or_create(
            schema,
            "specimen",
            "Specimen",
            0,
            [SampleRelationDefinition("Sampling to block", block, 1, None, 1, None)],
            attributes=[fixation, collection],
        )

        image = ImageSchema.get_or_create(
            schema, "wsi", "WSI", 3, [ImageRelationDefinition("Image of slide", slide)]
        )
        submitter = StringAttributeSchema.get_or_create(
            schema, "submitter", "Submitter"
        )
        project = ProjectSchema.get_or_create(schema, "project", "Project", [submitter])
        return schema
