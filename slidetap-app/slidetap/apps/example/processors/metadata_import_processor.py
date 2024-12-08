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


from typing import Any, Dict, Mapping
from uuid import UUID, uuid4

from slidetap.apps.example.schema import ExampleSchema
from slidetap.model.attribute import CodeAttribute, ListAttribute
from slidetap.model.image_status import ImageStatus
from slidetap.model.item import Image, Sample
from slidetap.model.schema.attribute_schema import (
    CodeAttributeSchema,
    ListAttributeSchema,
)
from slidetap.model.schema.item_schema import ImageSchema, SampleSchema
from slidetap.task.processors import MetadataImportProcessor


class ExampleMetadataImportProcessor(MetadataImportProcessor):

    @property
    def _schema(self):
        return ExampleSchema()

    @property
    def specimen_schema(self) -> SampleSchema:
        return self._schema.samples["specimen"]

    @property
    def block_schema(self) -> SampleSchema:
        return self._schema.samples["block"]

    @property
    def slide_schema(self) -> SampleSchema:
        return self._schema.samples["slide"]

    @property
    def image_schema(self) -> ImageSchema:
        return self._schema.images["wsi"]

    @property
    def collection_schema(self) -> CodeAttributeSchema:
        schema = self.specimen_schema.attributes["collection"]
        assert isinstance(schema, CodeAttributeSchema)
        return schema

    @property
    def fixation_schema(self):
        schema = self.specimen_schema.attributes["fixation"]
        assert isinstance(schema, CodeAttributeSchema)
        return schema

    @property
    def sampling_schema(self):
        schema = self.block_schema.attributes["block_sampling"]
        assert isinstance(schema, CodeAttributeSchema)
        return schema

    @property
    def embedding_schema(self):
        schema = self.block_schema.attributes["embedding"]
        assert isinstance(schema, CodeAttributeSchema)
        return schema

    @property
    def staining_schema(self):
        schema = self.slide_schema.attributes["staining"]
        assert isinstance(schema, ListAttributeSchema)
        return schema

    def run(self, project_uid: UUID, container: Dict[str, Any]):
        with self._app.app_context():
            specimens: Dict[str, Sample] = {}
            blocks: Dict[str, Sample] = {}
            slides: Dict[str, Sample] = {}
            for specimen in container["specimens"]:
                assert isinstance(specimen, Mapping)
                collection = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.collection_schema.uid,
                    mappable_value=specimen["collection"],
                )
                fixation = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.fixation_schema.uid,
                    mappable_value=specimen["fixation"],
                )
                specimen_model = Sample(
                    uid=UUID(int=0),
                    identifier=specimen["identifier"],
                    name=specimen["name"],
                    pseudonym=None,
                    selected=True,
                    valid=None,
                    valid_attributes=None,
                    valid_relations=None,
                    attributes={"collection": collection, "fixation": fixation},
                    project_uid=project_uid,
                    schema_display_name=self.specimen_schema.display_name,
                    schema_uid=self.specimen_schema.uid,
                )
                specimen_model = self._item_service.add(specimen_model)
                self._mapper_service.apply_mappers_to_item(specimen_model)
                specimens[specimen_model.identifier] = specimen_model

            for block in container["blocks"]:
                assert isinstance(block, Mapping)
                sampling = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.sampling_schema.uid,
                    mappable_value=block["sampling"],
                )
                embedding = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.embedding_schema.uid,
                    mappable_value=block["embedding"],
                )
                block_model = Sample(
                    uid=UUID(int=0),
                    identifier=block["identifier"],
                    name=block["name"],
                    pseudonym=None,
                    selected=True,
                    valid=None,
                    valid_attributes=None,
                    valid_relations=None,
                    attributes={"block_sampling": sampling, "embedding": embedding},
                    project_uid=project_uid,
                    schema_display_name=self.block_schema.display_name,
                    schema_uid=self.block_schema.uid,
                    parents=[
                        specimens[specimen_identifier].reference
                        for specimen_identifier in block["specimen_identifiers"]
                    ],
                )
                block_model = self._item_service.add(block_model)
                self._mapper_service.apply_mappers_to_item(block_model)
                blocks[block_model.identifier] = block_model

            for slide in container["slides"]:
                assert isinstance(slide, Mapping)
                primary_stain = CodeAttribute(
                    uid=uuid4(),
                    schema_uid=self.staining_schema.attribute.uid,
                    mappable_value=slide["primary_stain"],
                )
                secondary_stain = CodeAttribute(
                    uid=uuid4(),
                    schema_uid=self.staining_schema.attribute.uid,
                    mappable_value=slide["secondary_stain"],
                )
                staining = ListAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.staining_schema.uid,
                    original_value=(primary_stain, secondary_stain),
                )
                slide_model = Sample(
                    uid=UUID(int=0),
                    identifier=slide["identifier"],
                    name=slide["name"],
                    pseudonym=None,
                    selected=True,
                    valid=None,
                    valid_attributes=None,
                    valid_relations=None,
                    attributes={"staining": staining},
                    project_uid=project_uid,
                    schema_display_name=self.slide_schema.display_name,
                    schema_uid=self.slide_schema.uid,
                    parents=[blocks[slide["block_identifier"]].reference],
                )
                slide_model = self._item_service.add(slide_model)
                self._mapper_service.apply_mappers_to_item(slide_model)
                slides[slide_model.identifier] = slide_model

            for image in container["images"]:
                assert isinstance(image, Mapping)
                image = Image(
                    uid=uuid4(),
                    identifier=image["identifier"],
                    name=image["name"],
                    pseudonym=None,
                    selected=True,
                    valid=None,
                    valid_attributes=None,
                    valid_relations=None,
                    attributes={},
                    project_uid=project_uid,
                    schema_display_name=self.image_schema.display_name,
                    schema_uid=self.image_schema.uid,
                    status=ImageStatus.NOT_STARTED,
                    samples=[slides[image["slide_identifier"]].reference],
                )
                self._item_service.add(image)

            self._mapper_service.apply_to_project(project_uid)
            self._project_service.set_as_search_complete(project_uid)
