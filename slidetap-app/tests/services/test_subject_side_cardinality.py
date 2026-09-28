#    Copyright 2026 SECTRA AB
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

"""Tests for the cardinality a subject declares over what is attached to it.

An observation is on exactly one thing and an annotation on exactly one image,
so their own side of the relation is structural. The other side is a choice
the schema makes: a case may be nothing without a diagnosis, or a diagnosis
may be a bonus. The relation carries that choice, and the validator holds the
subject to it the same way it holds a slide to its images.
"""

from uuid import UUID, uuid4

import pytest

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseObservation,
    DatabaseSample,
)
from slidetap.model import Cardinality, Dataset, ImageFormat, Project
from slidetap.model.batch import BatchCreate
from slidetap.model.schema.dataset_schema import DatasetSchema
from slidetap.model.schema.item_relation import (
    AnnotationToImageRelation,
    ObservationToAnnotationRelation,
    ObservationToSampleRelation,
)
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.model.schema.project_schema import ProjectSchema
from slidetap.model.schema.root_schema import RootSchema
from slidetap.services import DatabaseService, SchemaService
from slidetap.services.validators.relation_validator import RelationValidator


@pytest.fixture()
def case_schema_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def diagnosis_schema_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def image_schema_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def annotation_schema_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def finding_schema_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def diagnoses_cardinality() -> Cardinality:
    """How many diagnoses a case may hold."""
    return Cardinality.ZERO_OR_MORE


@pytest.fixture()
def annotations_cardinality() -> Cardinality:
    """How many annotations an image may hold."""
    return Cardinality.ZERO_OR_MORE


@pytest.fixture()
def findings_cardinality() -> Cardinality:
    """How many findings an annotation may hold."""
    return Cardinality.ZERO_OR_MORE


@pytest.fixture()
def case_to_diagnosis(
    case_schema_uid: UUID,
    diagnosis_schema_uid: UUID,
    diagnoses_cardinality: Cardinality,
) -> ObservationToSampleRelation:
    return ObservationToSampleRelation(
        uid=uuid4(),
        name="Diagnosis of case",
        observation_uid=diagnosis_schema_uid,
        sample_uid=case_schema_uid,
        observation_title="Diagnosis",
        sample_title="Case",
        observations=diagnoses_cardinality,
    )


@pytest.fixture()
def image_to_annotation(
    image_schema_uid: UUID,
    annotation_schema_uid: UUID,
    annotations_cardinality: Cardinality,
) -> AnnotationToImageRelation:
    return AnnotationToImageRelation(
        uid=uuid4(),
        name="Annotation on image",
        annotation_uid=annotation_schema_uid,
        image_uid=image_schema_uid,
        annotation_title="Annotation",
        image_title="WSI",
        annotations=annotations_cardinality,
    )


@pytest.fixture()
def annotation_to_finding(
    annotation_schema_uid: UUID,
    finding_schema_uid: UUID,
    findings_cardinality: Cardinality,
) -> ObservationToAnnotationRelation:
    return ObservationToAnnotationRelation(
        uid=uuid4(),
        name="Finding of annotation",
        observation_uid=finding_schema_uid,
        annotation_uid=annotation_schema_uid,
        observation_title="Finding",
        annotation_title="Annotation",
        observations=findings_cardinality,
    )


@pytest.fixture()
def schema(
    case_schema_uid: UUID,
    diagnosis_schema_uid: UUID,
    image_schema_uid: UUID,
    annotation_schema_uid: UUID,
    finding_schema_uid: UUID,
    case_to_diagnosis: ObservationToSampleRelation,
    image_to_annotation: AnnotationToImageRelation,
    annotation_to_finding: ObservationToAnnotationRelation,
) -> RootSchema:
    """A case that holds diagnoses, and an image that holds annotations that
    hold findings. Nothing else, so that only the relations under test can
    make anything invalid."""
    return RootSchema(
        uid=uuid4(),
        name="Subject side cardinality",
        project=ProjectSchema(
            uid=uuid4(), name="project", display_name="Project", attributes={}
        ),
        dataset=DatasetSchema(
            uid=uuid4(), name="dataset", display_name="Dataset", attributes={}
        ),
        samples={
            case_schema_uid: SampleSchema(
                uid=case_schema_uid,
                name="case",
                display_name="Case",
                display_order=0,
                observations=(case_to_diagnosis,),
            )
        },
        observations={
            diagnosis_schema_uid: ObservationSchema(
                uid=diagnosis_schema_uid,
                name="diagnosis",
                display_name="Diagnosis",
                display_order=1,
                samples=(case_to_diagnosis,),
            ),
            finding_schema_uid: ObservationSchema(
                uid=finding_schema_uid,
                name="finding",
                display_name="Finding",
                display_order=4,
                annotations=(annotation_to_finding,),
            ),
        },
        images={
            image_schema_uid: ImageSchema(
                uid=image_schema_uid,
                name="wsi",
                display_name="WSI",
                display_order=2,
                annotations=(image_to_annotation,),
            )
        },
        annotations={
            annotation_schema_uid: AnnotationSchema(
                uid=annotation_schema_uid,
                name="annotation",
                display_name="Annotation",
                display_order=3,
                images=(image_to_annotation,),
                observations=(annotation_to_finding,),
            )
        },
    )


@pytest.fixture()
def batch_uid(
    sqlite_database_service: DatabaseService, dataset: Dataset, project: Project
) -> UUID:
    with sqlite_database_service.get_session() as session:
        sqlite_database_service.add_dataset(session, dataset)
        sqlite_database_service.add_project(session, project)
        return sqlite_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        ).uid


@pytest.fixture()
def validator(
    schema: RootSchema, sqlite_database_service: DatabaseService
) -> RelationValidator:
    return RelationValidator(SchemaService(schema), sqlite_database_service)


def _case(
    dataset: Dataset,
    batch_uid: UUID,
    case_schema_uid: UUID,
    diagnosis_schema_uid: UUID,
    diagnoses_selected: list[bool],
) -> DatabaseSample:
    """A case with a diagnosis per entry, each in or out of the project as the
    entry says."""
    case = DatabaseSample(dataset.uid, batch_uid, case_schema_uid, "CASE-1")
    for index, selected in enumerate(diagnoses_selected):
        DatabaseObservation(
            dataset.uid,
            batch_uid,
            diagnosis_schema_uid,
            f"DIAGNOSIS-{index}",
            item=case,
            selected=selected,
        )
    return case


@pytest.mark.unittest
class TestDiagnosesOfACase:
    @pytest.mark.parametrize(
        ("diagnoses_cardinality", "diagnosis_count", "valid"),
        [
            (Cardinality.ZERO_OR_MORE, 0, True),
            (Cardinality.ZERO_OR_MORE, 2, True),
            (Cardinality.ZERO_OR_ONE, 1, True),
            (Cardinality.ZERO_OR_ONE, 2, False),
            (Cardinality.ONE_OR_MORE, 0, False),
            (Cardinality.ONE_OR_MORE, 1, True),
            (Cardinality.ONE, 1, True),
            (Cardinality.ONE, 2, False),
        ],
    )
    def test_a_case_is_held_to_how_many_diagnoses_it_may_have(
        self,
        validator: RelationValidator,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        batch_uid: UUID,
        case_schema_uid: UUID,
        diagnosis_schema_uid: UUID,
        diagnosis_count: int,
        valid: bool,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            case = _case(
                dataset,
                batch_uid,
                case_schema_uid,
                diagnosis_schema_uid,
                [True] * diagnosis_count,
            )
            session.add(case)
            session.flush()

            # Act
            result = validator.validate_item_relations(case, session)

            # Assert
            assert result is valid
            assert case.valid_relations is valid

    @pytest.mark.parametrize("diagnoses_cardinality", [Cardinality.ONE_OR_MORE])
    def test_a_diagnosis_taken_out_of_the_project_counts_for_nothing(
        self,
        validator: RelationValidator,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        batch_uid: UUID,
        case_schema_uid: UUID,
        diagnosis_schema_uid: UUID,
    ):
        """What is going out with the case is what the case is judged on."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            case = _case(
                dataset, batch_uid, case_schema_uid, diagnosis_schema_uid, [False]
            )
            session.add(case)
            session.flush()

            # Act
            result = validator.validate_item_relations(case, session)

            # Assert
            assert result is False

    @pytest.mark.parametrize("diagnoses_cardinality", [Cardinality.ONE_OR_MORE])
    def test_a_diagnosis_the_import_has_not_delivered_is_not_held_against_the_case(
        self,
        validator: RelationValidator,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        batch_uid: UUID,
        case_schema_uid: UUID,
        diagnosis_schema_uid: UUID,
        case_to_diagnosis: ObservationToSampleRelation,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            case = _case(dataset, batch_uid, case_schema_uid, diagnosis_schema_uid, [])
            session.add(case)
            session.flush()

            # Act
            valid = validator.relations_are_valid(
                case, session, non_complete_relations=frozenset({case_to_diagnosis.uid})
            )

            # Assert
            assert valid

    @pytest.mark.parametrize("diagnoses_cardinality", [Cardinality.ONE_OR_MORE])
    def test_the_missing_diagnosis_is_named(
        self,
        validator: RelationValidator,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        batch_uid: UUID,
        case_schema_uid: UUID,
        diagnosis_schema_uid: UUID,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            case = _case(dataset, batch_uid, case_schema_uid, diagnosis_schema_uid, [])
            session.add(case)
            session.flush()

            # Act
            not_satisfied = validator.not_satisfied_relations(case, session)

            # Assert
            assert not_satisfied == ["Diagnosis of case"]

    def test_taking_the_case_out_revalidates_its_diagnoses(
        self,
        validator: RelationValidator,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        batch_uid: UUID,
        case_schema_uid: UUID,
        diagnosis_schema_uid: UUID,
    ):
        """A diagnosis is valid on a case that is in the project. Validating the
        case validates the diagnosis as the other side of the relation, so the
        diagnosis is not left saying it is fine after the case has gone."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            case = _case(
                dataset, batch_uid, case_schema_uid, diagnosis_schema_uid, [True]
            )
            session.add(case)
            session.flush()
            validator.validate_item_relations(case, session)
            diagnosis = next(iter(case.observations))
            assert diagnosis.valid_relations
            case.selected = False

            # Act
            validator.validate_item_relations(case, session)

            # Assert
            assert diagnosis.valid_relations is False


@pytest.mark.unittest
class TestAnnotationsOfAnImage:
    @staticmethod
    def _image(
        dataset: Dataset,
        batch_uid: UUID,
        image_schema_uid: UUID,
        annotation_schema_uid: UUID,
        annotation_count: int,
    ) -> DatabaseImage:
        image = DatabaseImage(
            dataset.uid, batch_uid, image_schema_uid, "WSI-1", ImageFormat.OTHER_WSI
        )
        for index in range(annotation_count):
            DatabaseAnnotation(
                dataset.uid,
                batch_uid,
                annotation_schema_uid,
                f"ANNOTATION-{index}",
                image=image,
            )
        return image

    @pytest.mark.parametrize(
        ("annotations_cardinality", "annotation_count", "valid"),
        [
            (Cardinality.ZERO_OR_MORE, 0, True),
            (Cardinality.ZERO_OR_ONE, 2, False),
            (Cardinality.ONE_OR_MORE, 0, False),
            (Cardinality.ONE_OR_MORE, 1, True),
        ],
    )
    def test_an_image_is_held_to_how_many_annotations_it_may_have(
        self,
        validator: RelationValidator,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        batch_uid: UUID,
        image_schema_uid: UUID,
        annotation_schema_uid: UUID,
        annotation_count: int,
        valid: bool,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            image = self._image(
                dataset,
                batch_uid,
                image_schema_uid,
                annotation_schema_uid,
                annotation_count,
            )
            session.add(image)
            session.flush()

            # Act
            result = validator.validate_item_relations(image, session)

            # Assert
            assert result is valid

    def test_an_annotation_on_an_image_out_of_the_project_is_not_valid(
        self,
        validator: RelationValidator,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        batch_uid: UUID,
        image_schema_uid: UUID,
        annotation_schema_uid: UUID,
    ):
        """The annotation's own side is structural, and still holds."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            image = self._image(
                dataset, batch_uid, image_schema_uid, annotation_schema_uid, 1
            )
            image.selected = False
            session.add(image)
            session.flush()
            annotation = next(iter(image.annotations))

            # Act
            result = validator.validate_item_relations(annotation, session)

            # Assert
            assert result is False
            assert validator.not_satisfied_relations(annotation, session) == [
                "Annotation on image"
            ]

    @pytest.mark.parametrize(
        ("findings_cardinality", "finding_count", "valid"),
        [
            (Cardinality.ZERO_OR_MORE, 0, True),
            (Cardinality.ONE_OR_MORE, 0, False),
            (Cardinality.ONE_OR_MORE, 1, True),
        ],
    )
    def test_an_annotation_is_held_to_how_many_findings_it_may_have(
        self,
        validator: RelationValidator,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        batch_uid: UUID,
        image_schema_uid: UUID,
        annotation_schema_uid: UUID,
        finding_schema_uid: UUID,
        finding_count: int,
        valid: bool,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            image = self._image(
                dataset, batch_uid, image_schema_uid, annotation_schema_uid, 1
            )
            annotation = next(iter(image.annotations))
            for index in range(finding_count):
                DatabaseObservation(
                    dataset.uid,
                    batch_uid,
                    finding_schema_uid,
                    f"FINDING-{index}",
                    item=annotation,
                )
            session.add(image)
            session.flush()

            # Act
            result = validator.validate_item_relations(annotation, session)

            # Assert
            assert result is valid
