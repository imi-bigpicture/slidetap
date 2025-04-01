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
from uuid import UUID

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
        return next(
            sample
            for sample in self._schema.samples.values()
            if sample.name == "specimen"
        )

    @property
    def block_schema(self) -> SampleSchema:
        return next(
            sample for sample in self._schema.samples.values() if sample.name == "block"
        )

    @property
    def slide_schema(self) -> SampleSchema:
        return next(
            sample for sample in self._schema.samples.values() if sample.name == "slide"
        )

    @property
    def image_schema(self) -> ImageSchema:
        return next(
            image for image in self._schema.images.values() if image.name == "wsi"
        )

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

    def run(
        self,
        batch_uid: UUID,
        container: Dict[str, Any],
    ):
        with self._database_service.get_session() as session:
            batch = self._database_service.get_batch(session, batch_uid)
            dataset_uid = batch.project.dataset.uid
            specimens: Dict[str, UUID] = {}
            blocks: Dict[str, UUID] = {}
            slides: Dict[str, UUID] = {}
            for specimen_data in container["specimens"]:
                assert isinstance(specimen_data, Mapping)
                collection = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.collection_schema.uid,
                    mappable_value=specimen_data["collection"],
                )
                fixation = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.fixation_schema.uid,
                    mappable_value=specimen_data["fixation"],
                )
                specimen = Sample(
                    uid=self._create_reproducible_uid(
                        dataset_uid,
                        self.specimen_schema.uid,
                        specimen_data["identifier"],
                    ),
                    identifier=specimen_data["identifier"],
                    name=specimen_data["name"],
                    pseudonym=None,
                    selected=True,
                    valid=None,
                    valid_attributes=None,
                    valid_relations=None,
                    attributes={"collection": collection, "fixation": fixation},
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                    schema_uid=self.specimen_schema.uid,
                )
                specimen = self._item_service.add(specimen, session=session)
                specimens[specimen.identifier] = specimen.uid

            for block_data in container["blocks"]:
                assert isinstance(block_data, Mapping)
                sampling = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.sampling_schema.uid,
                    mappable_value=block_data["sampling"],
                )
                embedding = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.embedding_schema.uid,
                    mappable_value=block_data["embedding"],
                )
                block = Sample(
                    uid=self._create_reproducible_uid(
                        dataset_uid, self.block_schema.uid, block_data["identifier"]
                    ),
                    identifier=block_data["identifier"],
                    name=block_data["name"],
                    pseudonym=None,
                    selected=True,
                    valid=None,
                    valid_attributes=None,
                    valid_relations=None,
                    attributes={"block_sampling": sampling, "embedding": embedding},
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                    schema_uid=self.block_schema.uid,
                    parents=[
                        specimens[specimen_identifier]
                        for specimen_identifier in block_data["specimen_identifiers"]
                    ],
                )
                block = self._item_service.add(block, session=session)
                blocks[block.identifier] = block.uid

            for slide_data in container["slides"]:
                assert isinstance(slide_data, Mapping)
                primary_stain = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.staining_schema.attribute.uid,
                    mappable_value=slide_data["primary_stain"],
                )
                secondary_stain = CodeAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.staining_schema.attribute.uid,
                    mappable_value=slide_data["secondary_stain"],
                )
                staining = ListAttribute(
                    uid=UUID(int=0),
                    schema_uid=self.staining_schema.uid,
                    original_value=[primary_stain, secondary_stain],
                )
                slide = Sample(
                    uid=self._create_reproducible_uid(
                        dataset_uid, self.slide_schema.uid, slide_data["identifier"]
                    ),
                    identifier=slide_data["identifier"],
                    name=slide_data["name"],
                    pseudonym=None,
                    selected=True,
                    valid=None,
                    valid_attributes=None,
                    valid_relations=None,
                    attributes={"staining": staining},
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                    schema_uid=self.slide_schema.uid,
                    parents=[blocks[slide_data["block_identifier"]]],
                )
                slide = self._item_service.add(slide, session=session)
                slides[slide.identifier] = slide.uid

            for image_data in container["images"]:
                assert isinstance(image_data, Mapping)
                image = Image(
                    uid=self._create_reproducible_uid(
                        dataset_uid, self.image_schema.uid, image_data["identifier"]
                    ),
                    identifier=image_data["identifier"],
                    name=image_data["name"],
                    pseudonym=None,
                    selected=True,
                    valid=None,
                    valid_attributes=None,
                    valid_relations=None,
                    attributes={},
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                    schema_uid=self.image_schema.uid,
                    status=ImageStatus.NOT_STARTED,
                    samples=[slides[image_data["slide_identifier"]]],
                )
                self._item_service.add(image, session=session)
            self._batch_service.set_as_search_complete(batch_uid, session)

    def _create_reproducible_uid(
        self, dataset_uid: UUID, schema_uid: UUID, identifier: str
    ) -> UUID:
        int_identifier = dataset_uid.int * schema_uid.int * hash(identifier)
        return UUID(int=int_identifier % 2**128)
