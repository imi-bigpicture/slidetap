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
from typing import Any, Dict, Iterable, Mapping
from uuid import UUID, uuid4

from fastapi import UploadFile
from slidetap.apps.example.model import ContainerModel
from slidetap.external_interfaces import (
    MetadataImportInterface,
)
from slidetap.image_processor.image_processor import (
    ImagePreProcessingSteps,
    ImageProcessor,
)
from slidetap.model import (
    Batch,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
    Image,
    ImageSchema,
    ImageStatus,
    Item,
    ListAttribute,
    ListAttributeSchema,
    Project,
    RootSchema,
    Sample,
    SampleSchema,
    StringAttribute,
)
from slidetap.services import SchemaService


class ExampleMetadataImportInterface(MetadataImportInterface[Dict[str, Any]]):
    def __init__(
        self,
        schema_service: SchemaService,
        image_pre_processor: ImageProcessor[ImagePreProcessingSteps],
    ):
        self._schema_service = schema_service
        self._schema = schema_service.root
        self._image_pre_processor = image_pre_processor

    @property
    def schema(self) -> RootSchema:
        return self._schema

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

    def parse_file(self, file: UploadFile) -> Dict[str, Any]:
        model = ContainerModel()
        input = file.file.read().decode()
        container = model.loads(input)
        assert isinstance(container, Dict)
        return container

    def create_project(self, name: str, dataset_uid: UUID) -> Project:
        submitter_schema = self._schema.project.attributes["submitter"]
        project = Project(
            uid=uuid4(),
            name=name,
            root_schema_uid=self.schema.uid,
            schema_uid=self.schema.project.uid,
            attributes={
                submitter_schema.tag: StringAttribute(
                    uid=uuid4(),
                    schema_uid=submitter_schema.uid,
                    original_value="test",
                )
            },
            dataset_uid=dataset_uid,
            created=datetime.datetime.now(),
        )
        return project

    def create_dataset(self, name: str) -> Dataset:
        dataset = Dataset(
            uid=uuid4(),
            name=name,
            schema_uid=self.schema.dataset.uid,
        )
        return dataset

    def search(
        self,
        batch: Batch,
        dataset: Dataset,
        search_parameters: Dict[str, Any],
    ) -> Iterable[Item]:
        logging.info(
            f"Searching for metadata in batch {batch.uid}, {search_parameters}."
        )

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
                    dataset.uid,
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
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.specimen_schema.uid,
            )
            specimens[specimen.identifier] = specimen.uid
            yield specimen

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
                    dataset.uid, self.block_schema.uid, block_data["identifier"]
                ),
                identifier=block_data["identifier"],
                name=block_data["name"],
                pseudonym=None,
                selected=True,
                valid=None,
                valid_attributes=None,
                valid_relations=None,
                attributes={"block_sampling": sampling, "embedding": embedding},
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.block_schema.uid,
                parents=[
                    specimens[specimen_identifier]
                    for specimen_identifier in block_data["specimen_identifiers"]
                ],
            )
            blocks[block.identifier] = block.uid
            yield block

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
                valid=False,
                updated_value=None,
                mapped_value=None,
                mappable_value=None,
                display_value=None,
                mapping_item_uid=None,
            )
            slide = Sample(
                uid=self._create_reproducible_uid(
                    dataset.uid, self.slide_schema.uid, slide_data["identifier"]
                ),
                identifier=slide_data["identifier"],
                name=slide_data["name"],
                pseudonym=None,
                selected=True,
                valid=False,
                valid_attributes=False,
                valid_relations=False,
                attributes={"staining": staining},
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.slide_schema.uid,
                parents=[blocks[slide_data["block_identifier"]]],
            )
            slides[slide.identifier] = slide.uid
            yield slide

        for image_data in search_parameters["images"]:
            assert isinstance(image_data, Mapping)
            image = Image(
                uid=self._create_reproducible_uid(
                    dataset.uid, self.image_schema.uid, image_data["identifier"]
                ),
                identifier=image_data["identifier"],
                name=image_data["name"],
                pseudonym=None,
                selected=True,
                valid=None,
                valid_attributes=None,
                valid_relations=None,
                attributes={},
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.image_schema.uid,
                status=ImageStatus.NOT_STARTED,
                samples=[slides[image_data["slide_identifier"]]],
            )
            yield image

    def import_image_metadata(
        self, image: Image, batch: Batch, project: Project
    ) -> Image:
        return self._image_pre_processor.run(image, batch, project)

    def _create_reproducible_uid(
        self, dataset_uid: UUID, schema_uid: UUID, identifier: str
    ) -> UUID:
        int_identifier = dataset_uid.int * schema_uid.int * hash(identifier)
        return UUID(int=int_identifier % 2**128)
