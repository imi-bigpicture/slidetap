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

import datetime
import logging
from typing import Any, Dict, Mapping
from uuid import UUID, uuid4

from slidetap.apps.example.model import ContainerModel
from slidetap.external_interfaces import (
    MetadataImportInterface,
)
from slidetap.image_processor.image_processor import ImagePreProcessor
from slidetap.model import Dataset, Project, RootSchema, StringAttribute
from slidetap.model.attribute import CodeAttribute, ListAttribute
from slidetap.model.image_status import ImageStatus
from slidetap.model.item import Image, Sample
from slidetap.model.schema.attribute_schema import (
    CodeAttributeSchema,
    ListAttributeSchema,
)
from slidetap.model.schema.item_schema import ImageSchema, SampleSchema
from slidetap.service_provider import ServiceProvider
from werkzeug.datastructures import FileStorage


class ExampleMetadataImportInterface(MetadataImportInterface[Dict[str, Any]]):
    def __init__(self, service_provider: ServiceProvider):
        self._schema_service = service_provider.schema_service
        self._database_service = service_provider.database_service
        self._item_service = service_provider.item_service
        self._batch_service = service_provider.batch_service
        self._image_pre_processor = ImagePreProcessor(service_provider)

    @property
    def schema(self) -> RootSchema:
        return self._schema_service.root

    @property
    def specimen_schema(self) -> SampleSchema:
        return next(
            sample
            for sample in self.schema.samples.values()
            if sample.name == "specimen"
        )

    @property
    def block_schema(self) -> SampleSchema:
        return next(
            sample for sample in self.schema.samples.values() if sample.name == "block"
        )

    @property
    def slide_schema(self) -> SampleSchema:
        return next(
            sample for sample in self.schema.samples.values() if sample.name == "slide"
        )

    @property
    def image_schema(self) -> ImageSchema:
        return next(
            image for image in self.schema.images.values() if image.name == "wsi"
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

    def parse_file(self, file: FileStorage) -> Dict[str, Any]:
        model = ContainerModel()
        input = file.stream.read().decode()
        container = model.loads(input)
        assert isinstance(container, Dict)
        return container

    def create_project(self, name: str, dataset_uid: UUID) -> Project:
        submitter_schema = self._schema_service.project.attributes["submitter"]
        project = Project(
            uuid4(),
            name,
            self.schema.uid,
            self.schema.project.uid,
            attributes={
                submitter_schema.tag: StringAttribute(
                    uuid4(),
                    submitter_schema.uid,
                    "test",
                )
            },
            dataset_uid=dataset_uid,
            created=datetime.datetime.now(),
        )
        return project

    def create_dataset(self, name: str) -> Dataset:
        dataset = Dataset(
            uuid4(),
            name,
            self.schema.dataset.uid,
        )
        return dataset

    def search(
        self,
        batch_uid: UUID,
        search_parameters: Dict[str, Any],
        **kwargs: Dict[str, Any],
    ) -> None:
        logging.info(
            f"Searching for metadata in batch {batch_uid}, {search_parameters}."
        )
        with self._database_service.get_session() as session:
            batch = self._database_service.get_batch(session, batch_uid)
            dataset_uid = batch.project.dataset.uid
            specimens: Dict[str, UUID] = {}
            blocks: Dict[str, UUID] = {}
            slides: Dict[str, UUID] = {}
            for specimen_data in search_parameters["specimens"]:
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

            for block_data in search_parameters["blocks"]:
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

            for slide_data in search_parameters["slides"]:
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

            for image_data in search_parameters["images"]:
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

    def import_image_metadata(self, image_uid: UUID, **kwargs: Dict[str, Any]) -> None:
        self._image_pre_processor.run(image_uid)

    def _create_reproducible_uid(
        self, dataset_uid: UUID, schema_uid: UUID, identifier: str
    ) -> UUID:
        int_identifier = dataset_uid.int * schema_uid.int * hash(identifier)
        return UUID(int=int_identifier % 2**128)
