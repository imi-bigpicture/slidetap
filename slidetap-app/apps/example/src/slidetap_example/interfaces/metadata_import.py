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
from typing import Any, Dict, Iterable
from uuid import UUID, uuid4

from slidetap.external_interfaces import MetadataImportInterface
from slidetap.image_processor.image_processor import ImageProcessor
from slidetap.model import (
    Batch,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
    File,
    Image,
    ImageFormat,
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
from slidetap.model.attribute import EnumAttribute
from slidetap.model.item import Observation
from slidetap.model.schema.attribute_schema import (
    EnumAttributeSchema,
    StringAttributeSchema,
)
from slidetap.model.schema.item_schema import ObservationSchema
from slidetap.services import SchemaService, StorageService

from slidetap_example.model import ContainerModel


class ExampleImagePreProcessor(ImageProcessor):
    def __init__(
        self,
        storage_service: StorageService,
        schema_service: SchemaService,
    ):
        super().__init__(
            storage_service=storage_service,
            schema_service=schema_service,
            steps=[],
        )


class ExampleMetadataImportInterface(MetadataImportInterface[Dict[str, Any]]):
    def __init__(
        self,
        schema_service: SchemaService,
        image_pre_processor: ExampleImagePreProcessor,
    ):
        self._schema_service = schema_service
        self._schema = schema_service.root
        self._image_pre_processor = image_pre_processor

    @property
    def schema(self) -> RootSchema:
        return self._schema

    @property
    def patient_schema(self) -> SampleSchema:
        return next(
            sample
            for sample in self.schema.samples.values()
            if sample.name == "patient"
        )

    @property
    def case_schema(self) -> SampleSchema:
        return next(
            sample for sample in self.schema.samples.values() if sample.name == "case"
        )

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
    def observation_schema(self) -> ObservationSchema:
        return next(
            sample
            for sample in self.schema.observations.values()
            if sample.name == "observation"
        )

    @property
    def sex_schema(self) -> EnumAttributeSchema:
        schema = self.patient_schema.attributes["sex"]
        assert isinstance(schema, EnumAttributeSchema)
        return schema

    @property
    def diagnose_schema(self) -> StringAttributeSchema:
        schema = self.observation_schema.attributes["diagnose"]
        assert isinstance(schema, StringAttributeSchema)
        return schema

    @property
    def report_schema(self) -> StringAttributeSchema:
        schema = self.observation_schema.private_attributes["report"]
        assert isinstance(schema, StringAttributeSchema)
        return schema

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

    def parse_file(self, file: File) -> Dict[str, Any]:
        assert (
            file.content_type == "application/json"
        ), f"Expected JSON file, got {file.content_type}."
        input = file.stream.read()
        container = ContainerModel.model_validate_json(input)
        return container.model_dump()

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
        container = ContainerModel.model_validate(search_parameters)
        patients: Dict[str, UUID] = {}
        cases: Dict[str, UUID] = {}
        specimens: Dict[str, UUID] = {}
        blocks: Dict[str, UUID] = {}
        slides: Dict[str, UUID] = {}
        for patient_data in container.patients:
            sex = EnumAttribute(
                uid=UUID(int=0),
                schema_uid=self.sex_schema.uid,
                original_value=patient_data.sex,
            )
            patient = Sample(
                uid=self._create_reproducible_uid(
                    dataset.uid, self.patient_schema.uid, patient_data.identifier
                ),
                identifier=patient_data.identifier,
                name=patient_data.name,
                pseudonym=None,
                selected=True,
                valid=None,
                valid_attributes=None,
                valid_relations=None,
                attributes={"sex": sex},
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.patient_schema.uid,
            )
            patients[patient.identifier] = patient.uid
            yield patient
        for case_data in container.cases:
            case = Sample(
                uid=self._create_reproducible_uid(
                    dataset.uid, self.case_schema.uid, case_data.identifier
                ),
                identifier=case_data.identifier,
                name=case_data.name,
                pseudonym=None,
                selected=True,
                valid=None,
                valid_attributes=None,
                valid_relations=None,
                attributes={},
                parents={
                    self.patient_schema.uid: [patients[case_data.patient_identifier]]
                },
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.case_schema.uid,
            )
            cases[case.identifier] = case.uid
            yield case
        for specimen_data in container.specimens:
            collection = CodeAttribute(
                uid=UUID(int=0),
                schema_uid=self.collection_schema.uid,
                mappable_value=specimen_data.collection,
            )
            fixation = CodeAttribute(
                uid=UUID(int=0),
                schema_uid=self.fixation_schema.uid,
                mappable_value=specimen_data.fixation,
            )
            specimen = Sample(
                uid=self._create_reproducible_uid(
                    dataset.uid,
                    self.specimen_schema.uid,
                    specimen_data.identifier,
                ),
                identifier=specimen_data.identifier,
                name=specimen_data.name,
                pseudonym=None,
                selected=True,
                valid=None,
                valid_attributes=None,
                valid_relations=None,
                attributes={"collection": collection, "fixation": fixation},
                parents={self.case_schema.uid: [cases[specimen_data.case_identifier]]},
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.specimen_schema.uid,
            )
            specimens[specimen.identifier] = specimen.uid
            yield specimen

        for block_data in container.blocks:
            sampling = CodeAttribute(
                uid=UUID(int=0),
                schema_uid=self.sampling_schema.uid,
                mappable_value=block_data.sampling,
            )
            embedding = CodeAttribute(
                uid=UUID(int=0),
                schema_uid=self.embedding_schema.uid,
                mappable_value=block_data.embedding,
            )
            block = Sample(
                uid=self._create_reproducible_uid(
                    dataset.uid, self.block_schema.uid, block_data.identifier
                ),
                identifier=block_data.identifier,
                name=block_data.name,
                pseudonym=None,
                selected=True,
                valid=None,
                valid_attributes=None,
                valid_relations=None,
                attributes={"block_sampling": sampling, "embedding": embedding},
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.block_schema.uid,
                parents={
                    self.specimen_schema.uid: [
                        specimens[specimen_identifier]
                        for specimen_identifier in block_data.specimen_identifiers
                    ]
                },
            )
            blocks[block.identifier] = block.uid
            yield block

        for slide_data in container.slides:
            primary_stain = CodeAttribute(
                uid=UUID(int=0),
                schema_uid=self.staining_schema.attribute.uid,
                mappable_value=slide_data.primary_stain,
            )
            secondary_stain = CodeAttribute(
                uid=UUID(int=0),
                schema_uid=self.staining_schema.attribute.uid,
                mappable_value=slide_data.secondary_stain,
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
                    dataset.uid, self.slide_schema.uid, slide_data.identifier
                ),
                identifier=slide_data.identifier,
                name=slide_data.name,
                pseudonym=None,
                selected=True,
                valid=False,
                valid_attributes=False,
                valid_relations=False,
                attributes={"staining": staining},
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.slide_schema.uid,
                parents={self.block_schema.uid: [blocks[slide_data.block_identifier]]},
            )
            slides[slide.identifier] = slide.uid
            yield slide

        for image_data in container.images:
            image = Image(
                uid=self._create_reproducible_uid(
                    dataset.uid, self.image_schema.uid, image_data.identifier
                ),
                identifier=image_data.identifier,
                name=image_data.name,
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
                samples={self.slide_schema.uid: [slides[image_data.slide_identifier]]},
                format=ImageFormat.OTHER_WSI,
            )
            yield image

        for observation_data in container.observations:
            diagnose = StringAttribute(
                uid=UUID(int=0),
                schema_uid=self.diagnose_schema.uid,
                original_value=observation_data.diagnose,
            )
            report = StringAttribute(
                uid=UUID(int=0),
                schema_uid=self.report_schema.uid,
                original_value=observation_data.report,
            )
            observation = Observation(
                uid=self._create_reproducible_uid(
                    dataset.uid,
                    self.observation_schema.uid,
                    observation_data.identifier,
                ),
                identifier=observation_data.identifier,
                name=observation_data.name,
                pseudonym=None,
                selected=True,
                valid=None,
                valid_attributes=None,
                valid_relations=None,
                attributes={"diagnose": diagnose},
                private_attributes={"report": report},
                dataset_uid=dataset.uid,
                batch_uid=batch.uid,
                schema_uid=self.observation_schema.uid,
                sample=(self.case_schema.uid, cases[observation_data.case_identifier]),
            )
            yield observation

    def import_image_metadata(
        self, image: Image, batch: Batch, project: Project
    ) -> Image:
        return self._image_pre_processor.run(image, batch, project)

    def _create_reproducible_uid(
        self, dataset_uid: UUID, schema_uid: UUID, identifier: str
    ) -> UUID:
        int_identifier = dataset_uid.int * schema_uid.int * hash(identifier)
        return UUID(int=int_identifier % 2**128)
