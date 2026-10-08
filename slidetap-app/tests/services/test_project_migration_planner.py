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

"""Planning the migration of a project from the example root to a second root
of its family, without a database.

The second root is the example schema with the sex of the patient changed, as
in `tests.conftest.other_schema`, and with a grade the case requires.
"""

import dataclasses
import datetime
from enum import Enum
from uuid import UUID, uuid4

import pytest
from slidetap_example import ExampleSchema

from slidetap.external_interfaces.implementations.migration import (
    DeclarativeSchemaMigration,
    EnumAttributeMigrator,
    ObjectMigrator,
)
from slidetap.model import (
    Code,
    CodeAttribute,
    Dataset,
    EnumAttribute,
    Item,
    ListAttribute,
    MetadataImportStatus,
    MetadataSearchItem,
    MigrationError,
    ObjectMigrationResult,
    Observation,
    Project,
    RootSchema,
    RootSchemaIndex,
    Sample,
    StringAttribute,
    StringAttributeSchema,
    UnresolvedAttributeMigration,
)
from slidetap.services.project_migration_planner import ProjectMigrationPlanner
from tests.conftest import OTHER_SEX_SCHEMA_UID

GRADE_SCHEMA_UID = UUID("2b8e4c1d-6f3a-4b5e-9c7d-1a2b3c4d5e6f")


class _ExampleSex(Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class _OtherSex(Enum):
    MALE = "Male"
    FEMALE = "Female"


class _SexMigration(DeclarativeSchemaMigration):
    """Migrates the sex of the patient with an enum migrator, which leaves a
    sex with no counterpart unresolved, and everything else as it is.

    What it does wrong, where a test asks it to, is what the planner has to
    refuse.
    """

    def __init__(self, schema: ExampleSchema, other_schema: RootSchema):
        sex = schema.patient.attributes["sex"]
        super().__init__(
            schema,
            other_schema,
            item_migrators=[
                ObjectMigrator[Item](
                    schema.patient,
                    other_schema.samples[schema.patient_schema_uid],
                    migrated_attributes=[
                        (sex, EnumAttributeMigrator(_ExampleSex, _OtherSex))
                    ],
                )
            ],
        )
        self._schema = schema
        self.dropped_tags: set[str] = set()
        """Tags left out."""
        self.project_schema_uid: UUID | None = None
        """The schema the project is put on instead of the target's."""
        self.wrong_kind = False
        """Whether a slide is put on the image schema."""
        self.wrong_tag = False
        """Whether the attributes are put under tags the target does not have."""

    def migrate_project(self, project: Project) -> ObjectMigrationResult:
        migrated = self._break(super().migrate_project(project))
        if self.project_schema_uid is not None:
            return dataclasses.replace(migrated, schema_uid=self.project_schema_uid)
        return migrated

    def migrate_dataset(self, dataset: Dataset) -> ObjectMigrationResult:
        return self._break(super().migrate_dataset(dataset))

    def migrate_item(self, item: Item) -> ObjectMigrationResult:
        migrated = self._break(super().migrate_item(item))
        if self.wrong_kind and item.schema_uid == self._schema.slide_schema_uid:
            return dataclasses.replace(
                migrated, schema_uid=self._schema.image_schema_uid
            )
        return migrated

    def _break(self, migrated: ObjectMigrationResult) -> ObjectMigrationResult:
        """The migrated object, changed as the test asks."""
        attributes = {
            f"{tag}-wrong" if self.wrong_tag else tag: attribute
            for tag, attribute in migrated.attributes.items()
            if tag not in self.dropped_tags
        }
        private_attributes = {
            tag: attribute
            for tag, attribute in migrated.private_attributes.items()
            if tag not in self.dropped_tags
        }
        return dataclasses.replace(
            migrated, attributes=attributes, private_attributes=private_attributes
        )


@pytest.fixture()
def target_schema(other_schema: RootSchema, schema: ExampleSchema) -> RootSchema:
    """The second root, with a grade the case requires."""
    case = other_schema.samples[schema.case_schema_uid]
    grade = StringAttributeSchema(
        uid=GRADE_SCHEMA_UID,
        tag="grade",
        name="grade",
        display_name="Grade",
        optional=False,
        read_only=False,
    )
    return other_schema.model_copy(
        update={
            "samples": {
                **other_schema.samples,
                case.uid: case.model_copy(update={"attributes": {"grade": grade}}),
            }
        }
    )


@pytest.fixture()
def migration(schema: ExampleSchema, target_schema: RootSchema) -> _SexMigration:
    return _SexMigration(schema, target_schema)


@pytest.fixture()
def planner(
    schema: ExampleSchema, target_schema: RootSchema, migration: _SexMigration
) -> ProjectMigrationPlanner:
    return ProjectMigrationPlanner(
        RootSchemaIndex(schema, is_default=False),
        RootSchemaIndex(target_schema, is_default=True),
        migration,
    )


class _Objects:
    """A project on the example root, with a patient of a sex the second root
    has, one of a sex it has not, one without a sex, a case, a slide, and an
    observation holding a private attribute."""

    def __init__(self, schema: ExampleSchema):
        self.dataset = Dataset(
            uid=uuid4(), name="dataset", schema_uid=schema.dataset.uid
        )
        self.project = Project(
            uid=uuid4(),
            name="project",
            root_schema_uid=schema.uid,
            schema_uid=schema.project.uid,
            dataset_uid=self.dataset.uid,
            created=datetime.datetime(2026, 1, 1),
        )
        self.batch_uid = uuid4()
        sex = schema.patient.attributes["sex"].uid
        self.male = self._sample(
            schema.patient_schema_uid,
            "patient-1",
            sex=EnumAttribute(uid=uuid4(), schema_uid=sex, original_value="M"),
        )
        self.other = self._sample(
            schema.patient_schema_uid,
            "patient-2",
            sex=EnumAttribute(uid=uuid4(), schema_uid=sex, original_value="Other"),
        )
        self.without_sex = self._sample(schema.patient_schema_uid, "patient-3")
        self.case = self._sample(schema.case_schema_uid, "case-1")
        staining = schema.slide.attributes["staining"]
        self.slide = self._sample(
            schema.slide_schema_uid,
            "slide-1",
            staining=ListAttribute(
                uid=uuid4(),
                schema_uid=staining.uid,
                original_value=[
                    CodeAttribute(
                        uid=uuid4(),
                        schema_uid=staining.attribute.uid,  # type: ignore
                        original_value=Code(code="HE", scheme="scheme", meaning="HE"),
                    )
                ],
            ),
        )
        report = schema.observation.private_attributes["report"]
        self.observation = Observation(
            uid=uuid4(),
            identifier="observation-1",
            dataset_uid=self.dataset.uid,
            batch_uid=self.batch_uid,
            schema_uid=schema.observation_schema_uid,
            sample=(schema.case_schema_uid, self.case.uid),
            private_attributes={
                "report": StringAttribute(
                    uid=uuid4(), schema_uid=report.uid, original_value="Benign"
                )
            },
        )

    @property
    def items(self) -> list[Item]:
        return [
            self.male,
            self.other,
            self.without_sex,
            self.case,
            self.slide,
            self.observation,
        ]

    @property
    def all(self) -> list[Project | Dataset | Item]:
        return [self.project, self.dataset, *self.items]

    def _sample(self, schema_uid: UUID, identifier: str, **attributes) -> Sample:
        return Sample(
            uid=uuid4(),
            identifier=identifier,
            dataset_uid=self.dataset.uid,
            batch_uid=self.batch_uid,
            schema_uid=schema_uid,
            attributes=attributes,
        )


@pytest.fixture()
def objects(schema: ExampleSchema) -> _Objects:
    return _Objects(schema)


@pytest.mark.unittest
class TestProjectMigrationPlanner:
    def test_every_object_is_put_on_its_target_schema(
        self,
        planner: ProjectMigrationPlanner,
        objects: _Objects,
        target_schema: RootSchema,
    ):
        # Act
        migrated = planner.migrate_objects(objects.all)

        # Assert
        assert [object_.source.uid for object_ in migrated] == [
            object_.uid for object_ in objects.all
        ]
        assert [object_.target_schema.uid for object_ in migrated] == [
            target_schema.project.uid,
            target_schema.dataset.uid,
            *(item.schema_uid for item in objects.items),
        ]
        male = migrated[2].target_attributes["sex"]
        assert isinstance(male, EnumAttribute)
        assert (male.schema_uid, male.original_value) == (OTHER_SEX_SCHEMA_UID, "Male")

    def test_an_unconverted_value_is_an_attribute_issue(
        self, planner: ProjectMigrationPlanner, objects: _Objects
    ):
        # Act
        (other,) = planner.migrate_objects([objects.other])
        issues = list(planner.create_attribute_issues(other))

        # Assert
        assert len(issues) == 1
        issue = issues[0]
        assert issue.target_attribute_schema_uid == OTHER_SEX_SCHEMA_UID
        assert issue.original is not None
        assert issue.original.uid == objects.other.attributes["sex"].uid
        assert issue.original.display_value == "Other"
        assert not issue.dropped

    def test_a_newly_required_attribute_is_an_attribute_issue(
        self, planner: ProjectMigrationPlanner, objects: _Objects
    ):
        # Act
        (case,) = planner.migrate_objects([objects.case])
        issues = list(planner.create_attribute_issues(case))

        # Assert
        grade = case.target_attributes["grade"]
        assert isinstance(grade, UnresolvedAttributeMigration)
        assert [
            (issue.target_attribute_schema_uid, issue.original, issue.problem)
            for issue in issues
        ] == [
            (
                GRADE_SCHEMA_UID,
                None,
                f"Required in {ExampleSchema().name} 2, has no value.",
            )
        ]

    def test_an_attribute_invalid_before_is_not_an_attribute_issue(
        self, planner: ProjectMigrationPlanner, objects: _Objects
    ):
        """The sex is required on both roots."""
        # Act
        (without_sex,) = planner.migrate_objects([objects.without_sex])

        # Assert
        assert list(without_sex.unresolved()) == []
        assert list(planner.create_attribute_issues(without_sex)) == []

    def test_a_dropped_attribute_is_an_attribute_issue(
        self,
        planner: ProjectMigrationPlanner,
        migration: _SexMigration,
        objects: _Objects,
    ):
        # Arrange
        migration.dropped_tags = {"report"}

        # Act
        (observation,) = planner.migrate_objects([objects.observation])
        issues = list(planner.create_attribute_issues(observation))

        # Assert
        report = objects.observation.private_attributes["report"]
        assert planner.get_dropped_attributes(observation) == [report]
        assert [
            (
                issue.source_attribute_schema_uid,
                issue.target_attribute_schema_uid,
                issue.problem,
            )
            for issue in issues
        ] == [
            (
                report.schema_uid,
                None,
                f"'Benign' of Report is dropped: it has no place in "
                f"{ExampleSchema().name} 2.",
            )
        ]
        assert issues[0].dropped

    def test_a_required_attribute_dropped_is_an_invalidated_attribute_issue(
        self,
        planner: ProjectMigrationPlanner,
        migration: _SexMigration,
        objects: _Objects,
    ):
        """The staining of the slide is required on both roots."""
        # Arrange
        migration.dropped_tags = {"staining"}

        # Act
        (slide,) = planner.migrate_objects([objects.slide])
        issues = list(planner.create_attribute_issues(slide))

        # Assert
        staining = objects.slide.attributes["staining"]
        assert planner.get_dropped_attributes(slide) == []
        assert len(issues) == 1
        issue = issues[0]
        assert not issue.dropped
        assert issue.original is not None
        assert issue.original.uid == staining.uid
        assert issue.problem == f"Required in {ExampleSchema().name} 2, has no value."

    def test_a_changed_plan_is_refused(
        self,
        planner: ProjectMigrationPlanner,
        migration: _SexMigration,
        objects: _Objects,
    ):
        # Arrange
        migrated = planner.migrate_objects(objects.all)
        planned = [
            (object_.source.uid, tag)
            for object_ in migrated
            for tag, _, _ in object_.unresolved()
        ]
        planner.refuse_changed_plan("project", migrated, planned, [])
        migration.dropped_tags = {"staining"}

        # Act & Assert
        with pytest.raises(MigrationError, match="no longer"):
            planner.refuse_changed_plan(
                "project", planner.migrate_objects(objects.all), planned, []
            )

    def test_a_project_off_the_target_schema_is_refused(
        self,
        planner: ProjectMigrationPlanner,
        migration: _SexMigration,
        objects: _Objects,
    ):
        # Arrange
        migration.project_schema_uid = uuid4()

        # Act & Assert
        with pytest.raises(MigrationError, match="target root"):
            planner.migrate_objects([objects.project])

    def test_an_item_on_another_kind_of_schema_is_refused(
        self,
        planner: ProjectMigrationPlanner,
        migration: _SexMigration,
        objects: _Objects,
    ):
        # Arrange
        migration.wrong_kind = True

        # Act & Assert
        with pytest.raises(MigrationError, match="same kind"):
            planner.migrate_objects([objects.slide])

    def test_an_attribute_off_the_target_schema_is_refused(
        self,
        planner: ProjectMigrationPlanner,
        migration: _SexMigration,
        objects: _Objects,
    ):
        # Arrange
        migration.wrong_tag = True

        # Act & Assert
        with pytest.raises(MigrationError, match="not an attribute"):
            planner.migrate_objects([objects.male])

    def test_a_search_item_is_moved_to_the_item_schema_of_its_kind(
        self,
        planner: ProjectMigrationPlanner,
        objects: _Objects,
        schema: ExampleSchema,
        monkeypatch: pytest.MonkeyPatch,
        migration: _SexMigration,
    ):
        # Arrange
        search_item = MetadataSearchItem(
            uid=uuid4(),
            batch_uid=objects.batch_uid,
            identifier="slide-1",
            schema_uid=schema.slide_schema_uid,
            status=MetadataImportStatus.COMPLETE,
        )

        # Act
        (moved,) = planner.migrate_search_items([search_item])
        monkeypatch.setattr(
            migration,
            "migrate_item_schema",
            lambda _: schema.images[schema.image_schema_uid],
        )

        # Assert
        assert moved.target_schema.uid == schema.slide_schema_uid
        with pytest.raises(MigrationError, match="search item"):
            planner.migrate_search_items([search_item])
