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
import hashlib
import logging
from collections import defaultdict
from typing import Any, Dict, Iterable, List
from uuid import UUID, uuid4

from slidetap.external_interfaces import MetadataImportInterface
from slidetap.image_processor.image_processor import ImageProcessor
from slidetap.model import (
    AnyItem,
    Batch,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
    EnumAttribute,
    File,
    Image,
    ImageFormat,
    ImageSchema,
    ImageStatus,
    ListAttribute,
    ListAttributeSchema,
    Observation,
    Project,
    RootSchema,
    Sample,
    SampleSchema,
    StringAttribute,
)
from slidetap.model.metadata_search_result import MetadataSearchResult
from slidetap.model.schema.attribute_schema import (
    EnumAttributeSchema,
    StringAttributeSchema,
)
from slidetap.model.schema.item_schema import ObservationSchema
from slidetap.services import SchemaService, StorageService

from slidetap_example.model import (
    BlockModel,
    CaseModel,
    ContainerModel,
    ImageModel,
    ObservationModel,
    PatientModel,
    SlideModel,
    SpecimenModel,
)


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
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

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
        if file.content_type != "application/json":
            raise ValueError(f"Expected JSON file, got {file.content_type}.")
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
    ) -> Iterable[MetadataSearchResult]:
        """One ``MetadataSearchResult`` per patient in the container.

        Each unit holds the patient and the full subtree reachable from
        them: cases → specimens → blocks → slides → images, plus the
        per-case observations. A block referenced from multiple specimens
        of the same patient is emitted once per parent specimen; the
        persistence layer merges its parent set when a unit re-adds an
        existing sample.
        """
        self._logger.info(
            f"Searching for metadata in batch {batch.uid}, {search_parameters}."
        )
        try:
            container = ContainerModel.model_validate(search_parameters)
        except Exception as exc:
            yield MetadataSearchResult.failed(
                identifier=batch.name,
                schema_uid=self.patient_schema.uid,
                message=f"Failed to parse search parameters: {exc}",
            )
            return

        cases_by_patient: Dict[str, List[CaseModel]] = defaultdict(list)
        for case in container.cases:
            cases_by_patient[case.patient_identifier].append(case)
        specimens_by_case: Dict[str, List[SpecimenModel]] = defaultdict(list)
        for specimen in container.specimens:
            specimens_by_case[specimen.case_identifier].append(specimen)
        blocks_by_specimen: Dict[str, List[BlockModel]] = defaultdict(list)
        for block in container.blocks:
            for specimen_identifier in block.specimen_identifiers:
                blocks_by_specimen[specimen_identifier].append(block)
        slides_by_block: Dict[str, List[SlideModel]] = defaultdict(list)
        for slide in container.slides:
            slides_by_block[slide.block_identifier].append(slide)
        images_by_slide: Dict[str, List[ImageModel]] = defaultdict(list)
        for image in container.images:
            images_by_slide[image.slide_identifier].append(image)
        observations_by_case: Dict[str, List[ObservationModel]] = defaultdict(list)
        for observation in container.observations:
            observations_by_case[observation.case_identifier].append(observation)

        for patient_data in container.patients:
            try:
                patient = self._build_patient(patient_data, dataset, batch)
                items: List[AnyItem] = [patient]

                # Walk level-by-level so every parent is emitted before any
                # of its children. Nesting per branch would emit a block
                # right after its first specimen and break parent lookup
                # when a block references multiple specimens of the same
                # patient.
                patient_cases = cases_by_patient.get(patient_data.identifier, [])
                items.extend(
                    self._build_case(case, dataset, batch) for case in patient_cases
                )
                patient_specimens = [
                    specimen
                    for case in patient_cases
                    for specimen in specimens_by_case.get(case.identifier, [])
                ]
                items.extend(
                    self._build_specimen(specimen, dataset, batch)
                    for specimen in patient_specimens
                )
                # Blocks may be reached from multiple specimens of the same
                # patient; dedup by identifier so each block is emitted once
                # with all its specimen parents resolvable at persist time.
                seen_block_ids: set[str] = set()
                patient_blocks: List[BlockModel] = []
                for specimen in patient_specimens:
                    for block in blocks_by_specimen.get(specimen.identifier, []):
                        if block.identifier in seen_block_ids:
                            continue
                        seen_block_ids.add(block.identifier)
                        patient_blocks.append(block)
                items.extend(
                    self._build_block(block, dataset, batch) for block in patient_blocks
                )
                patient_slides = [
                    slide
                    for block in patient_blocks
                    for slide in slides_by_block.get(block.identifier, [])
                ]
                items.extend(
                    self._build_slide(slide, dataset, batch) for slide in patient_slides
                )
                items.extend(
                    self._build_image(image, dataset, batch)
                    for slide in patient_slides
                    for image in images_by_slide.get(slide.identifier, [])
                )
                items.extend(
                    self._build_observation(observation, dataset, batch)
                    for case in patient_cases
                    for observation in observations_by_case.get(case.identifier, [])
                )
                yield MetadataSearchResult.succeeded(
                    identifier=patient_data.identifier,
                    schema_uid=self.patient_schema.uid,
                    items=items,
                    item_uid=patient.uid,
                )
            except Exception as exc:
                self._logger.exception(
                    f"Failed to build items for patient {patient_data.identifier}"
                )
                yield MetadataSearchResult.failed(
                    identifier=patient_data.identifier,
                    schema_uid=self.patient_schema.uid,
                    message=str(exc),
                )

    def import_image_metadata(
        self, image: Image, batch: Batch, project: Project, task_id: str
    ) -> Image:
        return self._image_pre_processor.run(image, batch, project, task_id)

    def _build_patient(
        self, patient_data: PatientModel, dataset: Dataset, batch: Batch
    ) -> Sample:
        sex = EnumAttribute(
            uid=UUID(int=0),
            schema_uid=self.sex_schema.uid,
            original_value=patient_data.sex,
        )
        return Sample(
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

    def _build_case(
        self, case_data: CaseModel, dataset: Dataset, batch: Batch
    ) -> Sample:
        patient_uid = self._create_reproducible_uid(
            dataset.uid, self.patient_schema.uid, case_data.patient_identifier
        )
        return Sample(
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
            parents={self.patient_schema.uid: [patient_uid]},
            dataset_uid=dataset.uid,
            batch_uid=batch.uid,
            schema_uid=self.case_schema.uid,
        )

    def _build_specimen(
        self, specimen_data: SpecimenModel, dataset: Dataset, batch: Batch
    ) -> Sample:
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
        case_uid = self._create_reproducible_uid(
            dataset.uid, self.case_schema.uid, specimen_data.case_identifier
        )
        return Sample(
            uid=self._create_reproducible_uid(
                dataset.uid, self.specimen_schema.uid, specimen_data.identifier
            ),
            identifier=specimen_data.identifier,
            name=specimen_data.name,
            pseudonym=None,
            selected=True,
            valid=None,
            valid_attributes=None,
            valid_relations=None,
            attributes={"collection": collection, "fixation": fixation},
            parents={self.case_schema.uid: [case_uid]},
            dataset_uid=dataset.uid,
            batch_uid=batch.uid,
            schema_uid=self.specimen_schema.uid,
        )

    def _build_block(
        self, block_data: BlockModel, dataset: Dataset, batch: Batch
    ) -> Sample:
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
        specimen_uids = [
            self._create_reproducible_uid(
                dataset.uid, self.specimen_schema.uid, specimen_identifier
            )
            for specimen_identifier in block_data.specimen_identifiers
        ]
        return Sample(
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
            parents={self.specimen_schema.uid: specimen_uids},
        )

    def _build_slide(
        self, slide_data: SlideModel, dataset: Dataset, batch: Batch
    ) -> Sample:
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
        block_uid = self._create_reproducible_uid(
            dataset.uid, self.block_schema.uid, slide_data.block_identifier
        )
        return Sample(
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
            parents={self.block_schema.uid: [block_uid]},
        )

    def _build_image(
        self, image_data: ImageModel, dataset: Dataset, batch: Batch
    ) -> Image:
        slide_uid = self._create_reproducible_uid(
            dataset.uid, self.slide_schema.uid, image_data.slide_identifier
        )
        return Image(
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
            samples={self.slide_schema.uid: [slide_uid]},
            format=ImageFormat.OTHER_WSI,
        )

    def _build_observation(
        self, observation_data: ObservationModel, dataset: Dataset, batch: Batch
    ) -> Observation:
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
        case_uid = self._create_reproducible_uid(
            dataset.uid, self.case_schema.uid, observation_data.case_identifier
        )
        return Observation(
            uid=self._create_reproducible_uid(
                dataset.uid, self.observation_schema.uid, observation_data.identifier
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
            sample=(self.case_schema.uid, case_uid),
        )

    def _create_reproducible_uid(
        self, dataset_uid: UUID, schema_uid: UUID, identifier: str
    ) -> UUID:
        digest = hashlib.sha256(
            f"{dataset_uid}|{schema_uid}|{identifier}".encode("utf-8")
        ).digest()
        return UUID(bytes=digest[:16])
