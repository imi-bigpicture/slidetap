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

"""Importer for json metadata using defined models."""

from typing import Any, Dict, Mapping, Union
from uuid import UUID

from flask import Flask, current_app
from slidetap.apps.example.model import parse_file
from slidetap.apps.example.schema import ExampleSchema
from slidetap.database.attribute import CodeAttribute, ListAttribute, StringAttribute
from slidetap.database.project import Image, Project, Sample
from slidetap.database.schema import (
    CodeAttributeSchema,
    ImageSchema,
    ListAttributeSchema,
    SampleSchema,
    Schema,
)
from slidetap.database.schema.attribute_schema import StringAttributeSchema
from slidetap.database.schema.project_schema import ProjectSchema
from slidetap.importer.metadata.metadata_importer import MetadataImporter
from slidetap.model import Session
from slidetap.services.mapper_service import MapperService
from slidetap.tasks.processors import MetadataImportProcessor
from werkzeug.datastructures import FileStorage


class ExampleMetadataImportProcessor(MetadataImportProcessor):
    def init_app(self, app: Flask):
        super().init_app(app)
        with app.app_context():
            self._schema = ExampleSchema.create()

    @property
    def specimen_schema(self):
        return SampleSchema.get(self._schema, "specimen")

    @property
    def block_schema(self):
        return SampleSchema.get(self._schema, "block")

    @property
    def slide_schema(self):
        return SampleSchema.get(self._schema, "slide")

    @property
    def image_schema(self):
        return ImageSchema.get(self._schema, "wsi")

    @property
    def collection_schema(self):
        return CodeAttributeSchema.get(self._schema, "collection")

    @property
    def fixation_schema(self):
        return CodeAttributeSchema.get(self._schema, "fixation")

    @property
    def sampling_schema(self):
        return CodeAttributeSchema.get(self._schema, "block_sampling")

    @property
    def embedding_schema(self):
        return CodeAttributeSchema.get(self._schema, "embedding")

    @property
    def stain_schema(self):
        return CodeAttributeSchema.get(self._schema, "stain")

    @property
    def staining_schema(self):
        return ListAttributeSchema.get(self._schema, "staining")

    def run(self, project_uid: UUID, container: Dict[str, Any]):
        with self._app.app_context():
            project = Project.get(project_uid)
            specimens: Dict[str, Sample] = {}
            blocks: Dict[str, Sample] = {}
            slides: Dict[str, Sample] = {}
            for specimen in container["specimens"]:
                assert isinstance(specimen, Mapping)
                collection = CodeAttribute(
                    self.collection_schema, mappable_value=specimen["collection"]
                )
                fixation = CodeAttribute(
                    self.fixation_schema, mappable_value=specimen["fixation"]
                )
                specimen_db = Sample(
                    project,
                    self.specimen_schema,
                    specimen["identifier"],
                    attributes=[collection, fixation],
                    name=specimen["name"],
                )
                specimens[specimen_db.identifier] = specimen_db

            for block in container["blocks"]:
                assert isinstance(block, Mapping)
                sampling = CodeAttribute(
                    self.sampling_schema, mappable_value=block["sampling"]
                )
                embedding = CodeAttribute(
                    self.embedding_schema, mappable_value=block["embedding"]
                )
                block_db = Sample(
                    project,
                    self.block_schema,
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
                    self.stain_schema,
                    mappable_value=slide["primary_stain"],
                )
                secondary_stain = CodeAttribute(
                    self.stain_schema,
                    mappable_value=slide["secondary_stain"],
                )
                staining = ListAttribute(
                    self.staining_schema, [primary_stain, secondary_stain]
                )
                slide_db = Sample(
                    project,
                    self.slide_schema,
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
                    self.image_schema,
                    image["identifier"],
                    slides[image["slide_identifier"]],
                    name=image["name"],
                )
            mapper_service = MapperService()
            mapper_service.apply_to_project(project)
            project.set_as_search_complete()


class ExampleMetadataImporter(MetadataImporter):
    def init_app(self, app: Flask):
        super().init_app(app)
        with app.app_context():
            self._schema = ExampleSchema.create()

    @property
    def schema(self) -> Schema:
        schema = Schema.get(ExampleSchema.uid)
        assert schema is not None
        return schema

    def create_project(self, session: Session, name: str) -> Project:
        schema = ProjectSchema.get_for_schema(self.schema)
        submitter_schema = StringAttributeSchema.get(self.schema, "submitter")
        submitter = StringAttribute(submitter_schema, "test")
        return Project(name, schema, attributes=[submitter])

    def search(
        self, session: Session, project: Project, file: Union[FileStorage, bytes]
    ):
        current_app.logger.info(f"Importing metadata for project {project}.")
        container = parse_file(file)
        self._scheduler.metadata_project_import(project, container=container)
