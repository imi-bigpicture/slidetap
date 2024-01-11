"""Example schema."""
from uuid import UUID
from slidetap.database.schema import Schema, SampleSchema, ImageSchema
from slidetap.database.schema.attribute_schema import (
    CodeAttributeSchema,
    ListAttributeSchema,
)


class ExampleSchema:
    @classmethod
    def create(cls) -> Schema:
        schema = Schema.get_or_create(
            UUID("752ee40c-5ebe-48cf-b384-7001239ee70d"), "Example schema"
        )
        stain = CodeAttributeSchema.get_or_create(schema, "stain", "Stain")
        staining = ListAttributeSchema.get_or_create(
            schema, "staining", "Staining", stain
        )

        slide = SampleSchema.get_or_create(schema, "slide", "Slide", 2, [], [staining])
        sampling_method = CodeAttributeSchema.get_or_create(
            schema, "block_sampling", "Sampling method"
        )
        embedding = CodeAttributeSchema.get_or_create(
            schema,
            "embedding",
            "Embedding",
        )

        block = SampleSchema.get_or_create(
            schema, "block", "Block", 1, [slide], [embedding, sampling_method]
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
            [block],
            attributes=[fixation, collection],
        )

        image = ImageSchema.get_or_create(schema, "wsi", "WSI", 3, [slide])
        return schema
