"""Importer for json metadata using defined models."""
from typing import Dict, Mapping, Union

from flask import Flask
from werkzeug.datastructures import FileStorage

from slidetap.apps.example.model import parse_file
from slidetap.apps.example.schema import ExampleSchema
from slidetap.database.attribute import CodeAttribute, ListAttribute
from slidetap.database.project import Image, Project, Sample
from slidetap.database.schema import (
    CodeAttributeSchema,
    ImageSchema,
    ListAttributeSchema,
    SampleSchema,
    Schema,
)
from slidetap.importer.metadata.metadata_importer import MetadataImporter
from slidetap.model import Session


class ExampleMetadataImporter(MetadataImporter):
    def init_app(self, app: Flask):
        super().init_app(app)
        with app.app_context():
            self._schema = ExampleSchema.create()

    @property
    def schema(self) -> Schema:
        return self._schema

    def search(
        self, session: Session, project: Project, file: Union[FileStorage, bytes]
    ):
        specimen_schema = SampleSchema.get(self.schema, "specimen")
        block_schema = SampleSchema.get(self.schema, "block")
        slide_schema = SampleSchema.get(self.schema, "slide")
        image_schema = ImageSchema.get(self.schema, "wsi")
        collection_schema = CodeAttributeSchema.get(self.schema, "collection")
        fixation_schema = CodeAttributeSchema.get(self.schema, "fixation")
        sampling_schema = CodeAttributeSchema.get(self.schema, "block_sampling")
        embedding_schema = CodeAttributeSchema.get(self.schema, "embedding")
        stain_schema = CodeAttributeSchema.get(self.schema, "stain")
        staining_schema = ListAttributeSchema.get(self.schema, "staining")

        container = parse_file(file)
        specimens: Dict[str, Sample] = {}
        blocks: Dict[str, Sample] = {}
        slides: Dict[str, Sample] = {}
        for specimen in container["specimens"]:
            assert isinstance(specimen, Mapping)
            collection = CodeAttribute(
                collection_schema, mappable_value=specimen["collection"]
            )
            fixation = CodeAttribute(
                fixation_schema, mappable_value=specimen["fixation"]
            )
            specimen_db = Sample(
                project,
                specimen_schema,
                specimen["identifier"],
                attributes=[collection, fixation],
                name=specimen["name"],
            )
            specimens[specimen_db.identifier] = specimen_db

        for block in container["blocks"]:
            assert isinstance(block, Mapping)
            sampling = CodeAttribute(sampling_schema, mappable_value=block["sampling"])
            embedding = CodeAttribute(
                embedding_schema, mappable_value=block["embedding"]
            )
            block_db = Sample(
                project,
                block_schema,
                block["identifier"],
                [
                    specimens[specimen_identifier]
                    for specimen_identifier in block["specimen_identifiers"]
                ],
                [sampling, embedding],
                name=block["name"],
            )
            blocks[block_db.identifier] = block_db

        for slide in container["slides"]:
            assert isinstance(slide, Mapping)
            primary_stain = CodeAttribute(
                stain_schema,
                mappable_value=slide["primary_stain"],
            )
            secondary_stain = CodeAttribute(
                stain_schema,
                mappable_value=slide["secondary_stain"],
            )
            staining = ListAttribute(staining_schema, [primary_stain, secondary_stain])
            slide_db = Sample(
                project,
                slide_schema,
                slide["identifier"],
                blocks[slide["block_identifier"]],
                [staining],
                name=slide["name"],
            )
            slides[slide_db.identifier] = slide_db

        for image in container["images"]:
            assert isinstance(image, Mapping)
            Image(
                project,
                image_schema,
                image["identifier"],
                slides[image["slide_identifier"]],
                name=image["name"],
            )
        project.set_as_search_complete()
