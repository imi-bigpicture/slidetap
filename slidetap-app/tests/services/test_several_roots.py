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

"""Projects on two roots in one application.

The second root is the example schema with the sex of the patient changed, as
a new version of a model changes an attribute: the patient schema keeps its
uid, and holds a sex of another uid with other allowed values. A patient is
only valid when read against the root of its own project.

Against a real SQLite database: which root an item is read against is decided
by the project its dataset belongs to.
"""

import datetime
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from slidetap_example import ExampleSchema

from slidetap.model import (
    BatchCreate,
    Dataset,
    EnumAttribute,
    NotFoundError,
    Project,
    ReviewLayout,
    ReviewUnitSchema,
    RootSchema,
    Sample,
)
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ItemService,
    MapperService,
    ReviewService,
    SchemaService,
    TagService,
    ValidationService,
)


@dataclass
class StoredProject:
    """A project stored with its dataset and a batch to add items to."""

    project: Project
    dataset: Dataset
    batch_uid: UUID


@pytest.fixture()
def reviewed_other_schema(other_schema: RootSchema) -> RootSchema:
    """The second root, where the patient is what a reviewer works through.

    The example root reviews nothing, so a review unit answered for by the
    wrong root is one that is either not found or found where there is none.
    """
    return other_schema.model_copy(
        update={
            "review_unit": ReviewUnitSchema(
                schema_uid=ExampleSchema().patient_schema_uid,
                layout=ReviewLayout(uid=uuid4(), name="review"),
            )
        }
    )


@pytest.fixture()
def schema_service(
    schema: ExampleSchema,
    reviewed_other_schema: RootSchema,
    schema_service_of: Callable[..., SchemaService],
) -> SchemaService:
    return schema_service_of(schema, reviewed_other_schema)


@pytest.fixture()
def validation_service(
    schema_service: SchemaService, sqlite_database_service: DatabaseService
) -> ValidationService:
    return ValidationService(schema_service, sqlite_database_service)


@pytest.fixture()
def review_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    sqlite_database_service: DatabaseService,
) -> ReviewService:
    return ReviewService(schema_service, validation_service, sqlite_database_service)


@pytest.fixture()
def mapper_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    review_service: ReviewService,
    sqlite_database_service: DatabaseService,
) -> MapperService:
    attribute_service = AttributeService(
        schema_service, validation_service, sqlite_database_service, review_service
    )
    return MapperService(
        attribute_service,
        validation_service,
        schema_service,
        sqlite_database_service,
        review_service,
    )


@pytest.fixture()
def item_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    review_service: ReviewService,
    mapper_service: MapperService,
    sqlite_database_service: DatabaseService,
) -> ItemService:
    attribute_service = AttributeService(
        schema_service, validation_service, sqlite_database_service, review_service
    )
    return ItemService(
        attribute_service,
        TagService(sqlite_database_service),
        mapper_service,
        schema_service,
        validation_service,
        sqlite_database_service,
        review_service,
    )


@pytest.mark.integration
class TestProjectsOnTwoRoots:
    @staticmethod
    def store_project(
        database_service: DatabaseService, root: RootSchema
    ) -> StoredProject:
        dataset = Dataset(uid=uuid4(), name="dataset", schema_uid=root.dataset.uid)
        project = Project(
            uid=uuid4(),
            name=f"project on {root.name}",
            root_schema_uid=root.uid,
            schema_uid=root.project.uid,
            dataset_uid=dataset.uid,
            created=datetime.datetime(2026, 1, 1),
        )
        with database_service.get_session() as session:
            database_service.add_dataset(session, dataset)
            database_service.add_project(session, project)
            batch = database_service.add_batch(
                session, BatchCreate(name="batch", project_uid=project.uid)
            )
            session.commit()
            return StoredProject(project, dataset, batch.uid)

    @staticmethod
    def patient(stored: StoredProject, sex_schema_uid: UUID, sex: str) -> Sample:
        return Sample(
            uid=uuid4(),
            identifier="patient-1",
            dataset_uid=stored.dataset.uid,
            batch_uid=stored.batch_uid,
            schema_uid=ExampleSchema().patient_schema_uid,
            attributes={
                "sex": EnumAttribute(
                    uid=uuid4(), schema_uid=sex_schema_uid, original_value=sex
                )
            },
        )

    def test_each_project_is_validated_against_its_own_root(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        item_service: ItemService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
    ):
        """The same value is valid in one root and not in the other, so a
        patient read against the wrong root is not valid."""
        # Arrange
        example = self.store_project(sqlite_database_service, schema)
        other = self.store_project(sqlite_database_service, reviewed_other_schema)
        example_sex = schema.patient.attributes["sex"].uid
        other_sex = reviewed_other_schema.samples[schema.patient_schema_uid]
        other_sex = other_sex.attributes["sex"].uid

        # Act
        on_example = item_service.add(self.patient(example, example_sex, "M"), [])
        on_other = item_service.add(self.patient(other, other_sex, "Male"), [])

        # Assert
        assert on_example.valid_attributes is True
        assert on_other.valid_attributes is True
        with sqlite_database_service.get_session() as session:
            roots = {
                uid: schema_service.root_of(
                    sqlite_database_service.get_item(session, uid)
                ).uid
                for uid in (on_example.uid, on_other.uid)
            }
        assert roots == {
            on_example.uid: schema.uid,
            on_other.uid: reviewed_other_schema.uid,
        }

    def test_a_value_of_the_other_root_is_not_valid(
        self,
        sqlite_database_service: DatabaseService,
        item_service: ItemService,
        schema: ExampleSchema,
    ):
        # Arrange
        example = self.store_project(sqlite_database_service, schema)
        example_sex = schema.patient.attributes["sex"].uid

        # Act
        on_example = item_service.add(self.patient(example, example_sex, "Male"), [])

        # Assert
        assert on_example.valid_attributes is False

    def test_each_project_is_reviewed_against_its_own_root(
        self,
        sqlite_database_service: DatabaseService,
        item_service: ItemService,
        review_service: ReviewService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
    ):
        """Only the second root has a review unit, so only its patient is one
        to review."""
        # Arrange
        example = self.store_project(sqlite_database_service, schema)
        other = self.store_project(sqlite_database_service, reviewed_other_schema)
        example_sex = schema.patient.attributes["sex"].uid
        other_sex = reviewed_other_schema.samples[schema.patient_schema_uid]
        other_sex = other_sex.attributes["sex"].uid
        item_service.add(self.patient(example, example_sex, "Unknown value"), [])
        item_service.add(self.patient(other, other_sex, "Unknown value"), [])

        # Act
        flagged_example = review_service.flag_invalid_review_units(example.dataset.uid)
        flagged_other = review_service.flag_invalid_review_units(other.dataset.uid)

        # Assert
        assert flagged_example == 0
        assert flagged_other == 1
        assert [
            item.identifier
            for item in review_service.get_review_queue(
                schema.patient_schema_uid, other.dataset.uid
            )
        ] == ["patient-1"]

    def test_what_a_root_does_not_have_is_not_found(
        self,
        sqlite_database_service: DatabaseService,
        item_service: ItemService,
        review_service: ReviewService,
        schema: ExampleSchema,
    ):
        """An item schema, or a layout, the root of the project does not have."""
        # Arrange
        stored = self.store_project(sqlite_database_service, schema)
        patient = item_service.add(
            self.patient(stored, schema.patient.attributes["sex"].uid, "M"), []
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="Item schema"):
            item_service.get_identities_for_schema(uuid4(), stored.dataset.uid)
        with pytest.raises(NotFoundError, match="Item schema"):
            review_service.get_review_queue(uuid4(), stored.dataset.uid)
        with pytest.raises(NotFoundError, match="Hierarchy layout"):
            item_service.get_hierarchy(patient.uid, uuid4())
        with pytest.raises(NotFoundError, match="Images layout"):
            item_service.get_images_for_item(patient.uid, None, uuid4())
        with pytest.raises(NotFoundError, match="Item"):
            item_service.get_images_for_item(uuid4(), schema.patient_schema_uid)

    def test_each_project_is_mapped_against_its_own_root(
        self,
        sqlite_database_service: DatabaseService,
        item_service: ItemService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
    ):
        """A mapper is of an attribute schema, and so maps only the projects on
        a root holding that attribute. What it maps to is validated against the
        root of the project the attribute is in."""
        # Arrange
        other = self.store_project(sqlite_database_service, reviewed_other_schema)
        other_sex = reviewed_other_schema.samples[schema.patient_schema_uid]
        other_sex = other_sex.attributes["sex"].uid
        mapper = mapper_service.get_or_create_mapper("sex", other_sex)
        mapper_service.get_or_create_mapping(
            mapper.uid,
            "man",
            EnumAttribute(uid=uuid4(), schema_uid=other_sex, original_value="Male"),
        )
        unmapped = self.patient(other, other_sex, "")
        unmapped.attributes["sex"].original_value = None
        unmapped.attributes["sex"].mappable_value = "man"

        # Act
        mapped = item_service.add(unmapped, [mapper.uid])

        # Assert
        assert mapped.attributes["sex"].value == "Male"
        assert mapped.valid_attributes is True
