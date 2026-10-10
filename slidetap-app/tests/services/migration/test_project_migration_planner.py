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
from collections.abc import Callable, Iterable
from enum import Enum
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from slidetap_example import ExampleSchema

from slidetap.database import DatabaseMigrationEntity
from slidetap.external_interfaces.implementations.migration import (
    AttributeMigrators,
    EntityMigrator,
    EnumAttributeMigrator,
    RootSchemaMigration,
)
from slidetap.model import (
    Code,
    CodeAttribute,
    Dataset,
    EntityMigrationResult,
    EnumAttribute,
    Item,
    ListAttribute,
    MetadataImportStatus,
    MetadataSearchItem,
    MigrationError,
    Observation,
    Project,
    RootSchema,
    RootSchemaIndex,
    Sample,
    StringAttribute,
    StringAttributeSchema,
    UnresolvedAttributeMigration,
)
from slidetap.services import SchemaService
from slidetap.services.migration.project_migration_planner import (
    ProjectMigrationPlan,
    ProjectMigrationPlanner,
)
from tests.conftest import OTHER_SEX_SCHEMA_UID, MovingMigrator

GRADE_SCHEMA_UID = UUID("2b8e4c1d-6f3a-4b5e-9c7d-1a2b3c4d5e6f")


class _ExampleSex(Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class _OtherSex(Enum):
    MALE = "Male"
    FEMALE = "Female"


class _PatientMigrator(EntityMigrator[Item]):
    """Migrates the sex of the patient with its migrator, and moves the rest as
    it is."""

    def __init__(
        self,
        schema: ExampleSchema,
        target_schema: RootSchema,
        sex_migrator: EnumAttributeMigrator,
    ):
        super().__init__(
            schema.patient, target_schema.samples[schema.patient_schema_uid]
        )
        self._sex_migrator = sex_migrator

    def migrate(self, entity: Item) -> EntityMigrationResult:
        attributes = self._move_all_except(entity.attributes, "sex")
        sex = entity.attributes.get("sex")
        if sex is not None:
            attributes["sex"] = self._migrate(
                sex, self._sex_migrator, self.target.attributes["sex"]
            )
        return EntityMigrationResult(
            schema_uid=self.target.uid,
            attributes=attributes,
            private_attributes=self._move_all_except(
                entity.private_attributes, private=True
            ),
        )


class _SexMigration(RootSchemaMigration):
    """Migrates the sex of the patient with an enum migrator, which leaves a
    sex with no counterpart unresolved, and moves everything else as it is.

    What it does wrong, where a test asks it to, is what the planner has to
    refuse.
    """

    def __init__(self, schema: ExampleSchema, other_schema: RootSchema):
        sex = schema.patient.attributes["sex"]
        sex_migrator = EnumAttributeMigrator(_ExampleSex, _OtherSex)
        attribute_migrators = AttributeMigrators(
            [
                (
                    sex,
                    sex_migrator,
                    other_schema.samples[schema.patient_schema_uid].attributes["sex"],
                )
            ]
        )
        other_items = {
            **other_schema.samples,
            **other_schema.images,
            **other_schema.observations,
        }
        super().__init__(
            schema,
            other_schema,
            attribute_migrators,
            project_migrator=MovingMigrator[Project](
                schema.project, other_schema.project
            ),
            dataset_migrator=MovingMigrator[Dataset](
                schema.dataset, other_schema.dataset
            ),
            item_migrators=[
                _PatientMigrator(schema, other_schema, sex_migrator),
                *(
                    MovingMigrator[Item](item, other_items[uid])
                    for uid, item in {
                        **schema.samples,
                        **schema.images,
                        **schema.observations,
                    }.items()
                    if uid != schema.patient_schema_uid
                ),
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
        self.unchanged: set[UUID] = set()
        """The entities returned as the same on the target root."""

    def migrate_project(self, project: Project) -> EntityMigrationResult | None:
        if project.uid in self.unchanged:
            return None
        migrated = self._break(super().migrate_project(project))
        if self.project_schema_uid is not None:
            return dataclasses.replace(migrated, schema_uid=self.project_schema_uid)
        return migrated

    def migrate_dataset(self, dataset: Dataset) -> EntityMigrationResult | None:
        if dataset.uid in self.unchanged:
            return None
        return self._break(super().migrate_dataset(dataset))

    def migrate_item(self, item: Item) -> EntityMigrationResult | None:
        if item.uid in self.unchanged:
            return None
        migrated = self._break(super().migrate_item(item))
        if self.wrong_kind and item.schema_uid == self._schema.slide_schema_uid:
            return dataclasses.replace(
                migrated, schema_uid=self._schema.image_schema_uid
            )
        return migrated

    def _break(self, migrated: EntityMigrationResult | None) -> EntityMigrationResult:
        """The migrated entity, changed as the test asks."""
        assert migrated is not None
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
    decoy: Decoy,
    schema: ExampleSchema,
    target_schema: RootSchema,
    migration: _SexMigration,
) -> ProjectMigrationPlanner:
    """A planner of the migration from the example root to the second root,
    with the roots and the migration of a schema service without a database."""
    schema_service = decoy.mock(cls=SchemaService)
    decoy.when(schema_service.get_root(schema.uid)).then_return(
        RootSchemaIndex(schema, is_default=False)
    )
    decoy.when(schema_service.get_root(target_schema.uid)).then_return(
        RootSchemaIndex(target_schema, is_default=True)
    )
    decoy.when(schema_service.migration_of(schema.uid)).then_return(migration)
    return ProjectMigrationPlanner(schema_service)


_Plan = Callable[..., ProjectMigrationPlan]


@pytest.fixture()
def plan(
    planner: ProjectMigrationPlanner, schema: ExampleSchema, target_schema: RootSchema
) -> _Plan:
    """Plans the migration of entities and search items to the second root."""

    def plan(
        entities: Iterable[Project | Dataset | Item],
        search_items: Iterable[MetadataSearchItem] = (),
    ) -> ProjectMigrationPlan:
        return planner.plan(schema.uid, target_schema.uid, entities, search_items)

    return plan


class _Entities:
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
def entities(schema: ExampleSchema) -> _Entities:
    return _Entities(schema)


@pytest.mark.unittest
class TestProjectMigrationPlanner:
    def test_every_entity_is_put_on_its_target_schema(
        self,
        plan: _Plan,
        entities: _Entities,
        target_schema: RootSchema,
    ):
        # Act
        migrated = plan(entities.all).entities

        # Assert
        assert [entity.source.uid for entity in migrated] == [
            entity.uid for entity in entities.all
        ]
        assert [entity.target_schema.uid for entity in migrated] == [
            target_schema.project.uid,
            target_schema.dataset.uid,
            *(item.schema_uid for item in entities.items),
        ]
        male = migrated[2].target_attributes["sex"]
        assert isinstance(male, EnumAttribute)
        assert (male.schema_uid, male.original_value) == (OTHER_SEX_SCHEMA_UID, "Male")

    def test_an_unconverted_value_is_an_attribute_issue(
        self, plan: _Plan, entities: _Entities
    ):
        # Act
        planned = plan([entities.other])
        (other,) = planned.entities
        issues = planned.attribute_issues[other.source.uid]

        # Assert
        assert len(issues) == 1
        issue = issues[0]
        assert issue.target_attribute_schema_uid == OTHER_SEX_SCHEMA_UID
        assert issue.original is not None
        assert issue.original.uid == entities.other.attributes["sex"].uid
        assert issue.original.display_value == "Other"
        assert not issue.dropped

    def test_a_newly_required_attribute_is_an_attribute_issue(
        self, plan: _Plan, entities: _Entities
    ):
        # Act
        planned = plan([entities.case])
        (case,) = planned.entities
        issues = planned.attribute_issues[case.source.uid]

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
        self, plan: _Plan, entities: _Entities
    ):
        """The sex is required on both roots."""
        # Act
        planned = plan([entities.without_sex])
        (without_sex,) = planned.entities

        # Assert
        assert list(without_sex.unresolved()) == []
        assert planned.attribute_issues[without_sex.source.uid] == []

    def test_a_dropped_attribute_is_an_attribute_issue(
        self,
        plan: _Plan,
        migration: _SexMigration,
        entities: _Entities,
    ):
        # Arrange
        migration.dropped_tags = {"report"}

        # Act
        planned = plan([entities.observation])
        (observation,) = planned.entities
        issues = planned.attribute_issues[observation.source.uid]

        # Assert
        report = entities.observation.private_attributes["report"]
        assert observation.dropped_attributes == [report]
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
        plan: _Plan,
        migration: _SexMigration,
        entities: _Entities,
    ):
        """The staining of the slide is required on both roots."""
        # Arrange
        migration.dropped_tags = {"staining"}

        # Act
        planned = plan([entities.slide])
        (slide,) = planned.entities
        issues = planned.attribute_issues[slide.source.uid]

        # Assert
        staining = entities.slide.attributes["staining"]
        assert slide.dropped_attributes == []
        assert len(issues) == 1
        issue = issues[0]
        assert not issue.dropped
        assert issue.original is not None
        assert issue.original.uid == staining.uid
        assert issue.problem == f"Required in {ExampleSchema().name} 2, has no value."

    def test_a_changed_plan_is_refused(
        self,
        planner: ProjectMigrationPlanner,
        plan: _Plan,
        migration: _SexMigration,
        entities: _Entities,
    ):
        # Arrange
        planned = plan(entities.all)
        stored = [
            DatabaseMigrationEntity(
                entity.source.uid,
                entity.target_schema.uid,
                entity.identifier,
                position,
                planned.attribute_issues[entity.source.uid],
            )
            for position, entity in enumerate(planned.entities)
        ]
        planner.refuse_changed_plan(plan(entities.all), "project", stored)
        migration.dropped_tags = {"staining"}

        # Act & Assert
        with pytest.raises(MigrationError, match="no longer"):
            planner.refuse_changed_plan(plan(entities.all), "project", stored)

    def test_a_project_off_the_target_schema_is_refused(
        self,
        plan: _Plan,
        migration: _SexMigration,
        entities: _Entities,
    ):
        # Arrange
        migration.project_schema_uid = uuid4()

        # Act & Assert
        with pytest.raises(MigrationError, match="target root"):
            plan([entities.project])

    def test_an_item_on_another_kind_of_schema_is_refused(
        self,
        plan: _Plan,
        migration: _SexMigration,
        entities: _Entities,
    ):
        # Arrange
        migration.wrong_kind = True

        # Act & Assert
        with pytest.raises(MigrationError, match="same kind"):
            plan([entities.slide])

    def test_an_attribute_off_the_target_schema_is_refused(
        self,
        plan: _Plan,
        migration: _SexMigration,
        entities: _Entities,
    ):
        # Arrange
        migration.wrong_tag = True

        # Act & Assert
        with pytest.raises(MigrationError, match="not an attribute"):
            plan([entities.male])

    def test_an_entity_left_as_it_is_on_the_same_schema_is_left_out(
        self,
        plan: _Plan,
        migration: _SexMigration,
        entities: _Entities,
    ):
        """The project, the dataset, and the slide are the same on both roots."""
        # Arrange
        migration.unchanged = {
            entities.project.uid,
            entities.dataset.uid,
            entities.slide.uid,
        }

        # Act
        planned = plan(entities.all)

        # Assert
        assert [entity.source.uid for entity in planned.entities] == [
            entities.male.uid,
            entities.other.uid,
            entities.without_sex.uid,
            entities.case.uid,
            entities.observation.uid,
        ]
        assert entities.slide.uid not in planned.attribute_issues

    @pytest.mark.parametrize("name", ["male", "case"])
    def test_an_entity_left_as_it_is_on_a_changed_schema_is_refused(
        self,
        plan: _Plan,
        migration: _SexMigration,
        entities: _Entities,
        name: str,
    ):
        """The patient has a sex of other values, and the case a grade."""
        # Arrange
        entity = getattr(entities, name)
        migration.unchanged = {entity.uid}

        # Act & Assert
        with pytest.raises(MigrationError, match=f"left {entity.identifier}"):
            plan([entity])

    def test_a_search_item_is_moved_to_the_item_schema_of_its_kind(
        self,
        plan: _Plan,
        entities: _Entities,
        schema: ExampleSchema,
        monkeypatch: pytest.MonkeyPatch,
        migration: _SexMigration,
    ):
        # Arrange
        search_item = MetadataSearchItem(
            uid=uuid4(),
            batch_uid=entities.batch_uid,
            identifier="slide-1",
            schema_uid=schema.slide_schema_uid,
            status=MetadataImportStatus.COMPLETE,
        )

        # Act
        (moved,) = plan([], [search_item]).search_items
        monkeypatch.setattr(
            migration,
            "migrate_item_schema",
            lambda _: schema.images[schema.image_schema_uid],
        )

        # Assert
        assert moved.target_schema.uid == schema.slide_schema_uid
        with pytest.raises(MigrationError, match="search item"):
            plan([], [search_item])
