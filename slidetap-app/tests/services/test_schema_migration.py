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

"""Moving a project from the example root to a second root of its family.

The second root is the example schema with the sex of the patient changed: its
allowed values are "Male" and "Female" rather than "M", "F", "Other", and
"Unknown", under another uid. The migration converts the sex, leaves one that
has no counterpart to the curator, and moves every other attribute as it is.

Against a real SQLite database: what is checked is what is saved.
"""

import dataclasses
import datetime
from collections.abc import Callable, Mapping
from enum import Enum
from typing import TypeVar
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from slidetap_example import ExampleSchema
from sqlalchemy import select

from slidetap.cli.mappers import MapperSetUp
from slidetap.database import (
    DatabaseAttribute,
    DatabaseAttributeMigrationIssue,
    DatabaseMapper,
    DatabaseMappingItem,
    DatabaseMetadataSearchItem,
    DatabaseProject,
    DatabaseReviewIssue,
    DatabaseUnmappedValue,
)
from slidetap.external_interfaces import MapperInjectorInterface, SchemaInterface
from slidetap.external_interfaces.implementations.migration import (
    DeclarativeSchemaMigration,
    EnumAttributeMigrator,
    ObjectMigrator,
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnyAttribute,
    AttributeMigrationIssue,
    BatchCreate,
    BatchStatus,
    Code,
    CodeAttribute,
    Dataset,
    EnumAttribute,
    Item,
    ItemSchema,
    ListAttribute,
    Mapper,
    MapperGroup,
    MetadataImportStatus,
    MigrationError,
    MigrationObjectKind,
    MigrationStatus,
    NotAllowedActionError,
    NotFoundError,
    ObjectMigrationResult,
    Observation,
    Project,
    ProjectMigration,
    ProjectNotEditableError,
    ProjectStatus,
    ReviewLayout,
    ReviewUnitSchema,
    RootSchema,
    Sample,
    StringAttribute,
    StringAttributeSchema,
    UnresolvedAttribute,
)
from slidetap.model.item_select import ItemSelect
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    ItemService,
    MapperService,
    MigrationService,
    ProjectService,
    ReviewService,
    SchemaService,
    StorageService,
    TagService,
    ValidationService,
)
from slidetap.task.tasks import complete_schema_migration, plan_schema_migration
from tests.conftest import OTHER_ROOT_SCHEMA_UID, OTHER_SEX_SCHEMA_UID

_V = TypeVar("_V")


class _ExampleSex(Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class _OtherSex(Enum):
    MALE = "Male"
    FEMALE = "Female"


class _SexMigration(DeclarativeSchemaMigration):
    """Moves projects from the example root to the second, migrating the sex
    of the patient with an enum migrator, which leaves a sex with no
    counterpart unresolved, for the curator to resolve.

    What it does wrong, where a test asks it to, is what the migration service
    has to refuse.
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
        self.wrong_kind = False
        """Whether a slide is put on the image schema."""
        self.wrong_tag = False
        """Whether the attributes are put under tags the target does not have."""
        self.dropped_tags: set[str] = set()
        """Tags left out."""
        self.unresolved_tags: set[str] = set()
        """Tags left unresolved, with the attribute moved as it is proposed."""
        self.wrong_unresolved: str | None = None
        """How an unresolved attribute is returned wrong: under a tag the
        target does not have, proposed on another schema, or among the private
        attributes."""

    def migrate_project(self, project: Project) -> ObjectMigrationResult:
        return self._break(super().migrate_project(project))

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
        attributes = self._without_dropped(migrated.attributes)
        private_attributes = self._without_dropped(migrated.private_attributes)
        for moved in (attributes, private_attributes):
            for tag in self.unresolved_tags & moved.keys():
                attribute = moved[tag]
                assert not isinstance(attribute, UnresolvedAttribute)
                moved[tag] = UnresolvedAttribute(attribute, attribute, "Asked")
        if self.wrong_tag:
            attributes = {f"{tag}-wrong": value for tag, value in attributes.items()}
        for moved in (attributes, private_attributes):
            for tag, value in list(moved.items()):
                if not isinstance(value, UnresolvedAttribute):
                    continue
                if self.wrong_unresolved == "tag":
                    moved[f"{tag}-wrong"] = moved.pop(tag)
                elif self.wrong_unresolved == "proposal":
                    moved[tag] = dataclasses.replace(value, proposed=value.original)
        if self.wrong_unresolved == "private":
            for tag, value in list(attributes.items()):
                if isinstance(value, UnresolvedAttribute):
                    private_attributes[tag] = attributes.pop(tag)
        return ObjectMigrationResult(
            schema_uid=migrated.schema_uid,
            attributes=attributes,
            private_attributes=private_attributes,
        )

    def _without_dropped(self, values: Mapping[str, _V]) -> dict[str, _V]:
        return {
            tag: value for tag, value in values.items() if tag not in self.dropped_tags
        }


@pytest.fixture()
def reviewed_other_schema(other_schema: RootSchema) -> RootSchema:
    """The second root, where the patient is what a reviewer works through."""
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
    migration: "_SexMigration",
    schema_service_of: Callable[..., SchemaService],
) -> SchemaService:
    return schema_service_of(
        reviewed_other_schema, schema, migrations={schema.uid: migration}
    )


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
def attribute_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    review_service: ReviewService,
    sqlite_database_service: DatabaseService,
) -> AttributeService:
    return AttributeService(
        schema_service, validation_service, sqlite_database_service, review_service
    )


@pytest.fixture()
def mapper_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    review_service: ReviewService,
    attribute_service: AttributeService,
    sqlite_database_service: DatabaseService,
) -> MapperService:
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
    attribute_service: AttributeService,
    mapper_service: MapperService,
    sqlite_database_service: DatabaseService,
) -> ItemService:
    return ItemService(
        attribute_service,
        TagService(sqlite_database_service),
        mapper_service,
        schema_service,
        validation_service,
        sqlite_database_service,
        review_service,
    )


@pytest.fixture()
def migration(schema: ExampleSchema, other_schema: RootSchema) -> _SexMigration:
    return _SexMigration(schema, other_schema)


@pytest.fixture()
def migration_service(
    schema_service: SchemaService,
    sqlite_database_service: DatabaseService,
    attribute_service: AttributeService,
    validation_service: ValidationService,
    review_service: ReviewService,
    mapper_service: MapperService,
) -> MigrationService:
    return MigrationService(
        schema_service,
        sqlite_database_service,
        attribute_service,
        validation_service,
        review_service,
        mapper_service,
    )


class _StoredProject:
    """A project on the example root, with two patients, a slide, and an
    observation holding a private attribute."""

    def __init__(
        self,
        database_service: DatabaseService,
        item_service: ItemService,
        schema: ExampleSchema,
    ):
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
        with database_service.get_session() as session:
            database_service.add_dataset(session, self.dataset)
            database_service.add_project(session, self.project)
            self.batch_uid = database_service.add_batch(
                session, BatchCreate(name="batch", project_uid=self.project.uid)
            ).uid
            session.commit()
        sex = schema.patient.attributes["sex"].uid
        self.patient = item_service.add(
            self._sample(schema.patient_schema_uid, "patient-1").model_copy(
                update={
                    "attributes": {
                        "sex": EnumAttribute(
                            uid=uuid4(),
                            schema_uid=sex,
                            original_value="M",
                            updated_value="F",
                        )
                    }
                }
            ),
            [],
        )
        self.other_patient = item_service.add(
            self._sample(schema.patient_schema_uid, "patient-2").model_copy(
                update={
                    "attributes": {
                        "sex": EnumAttribute(
                            uid=uuid4(), schema_uid=sex, original_value="Other"
                        )
                    }
                }
            ),
            [],
        )
        self.case = item_service.add(
            self._sample(schema.case_schema_uid, "case-1").model_copy(
                update={"parents": {schema.patient_schema_uid: [self.patient.uid]}}
            ),
            [],
        )
        staining = schema.slide.attributes["staining"]
        self.slide = item_service.add(
            self._sample(schema.slide_schema_uid, "slide-1").model_copy(
                update={
                    "attributes": {
                        "staining": ListAttribute(
                            uid=uuid4(),
                            schema_uid=staining.uid,
                            original_value=[
                                CodeAttribute(
                                    uid=uuid4(),
                                    schema_uid=staining.attribute.uid,  # type: ignore
                                    original_value=Code(
                                        code="HE", scheme="scheme", meaning="HE"
                                    ),
                                )
                            ],
                        )
                    }
                }
            ),
            [],
        )
        report = schema.observation.private_attributes["report"]
        self.observation = item_service.add(
            Observation(
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
            ),
            [],
        )

    def can_migrate(
        self, database_service: DatabaseService, schema_service: SchemaService
    ) -> bool:
        """Whether the project can be migrated now, as its root schema support says."""
        with database_service.get_session() as session:
            project = database_service.get_project(session, self.project.uid)
            return (
                schema_service.support_of(project).migrate_refusal(
                    DatabaseService.has_stored_batches(session, project),
                    DatabaseService.has_busy_batches(session, project),
                )
                is None
            )

    def _sample(self, schema_uid: UUID, identifier: str) -> Sample:
        return Sample(
            uid=uuid4(),
            identifier=identifier,
            dataset_uid=self.dataset.uid,
            batch_uid=self.batch_uid,
            schema_uid=schema_uid,
        )


@pytest.fixture()
def stored(
    sqlite_database_service: DatabaseService,
    schema: ExampleSchema,
    schema_service_of: Callable[..., SchemaService],
) -> _StoredProject:
    """Stored while the example root was the root of new projects, before
    the application was upgraded to the second root."""
    schema_service = schema_service_of(schema)
    validation_service = ValidationService(schema_service, sqlite_database_service)
    review_service = ReviewService(
        schema_service, validation_service, sqlite_database_service
    )
    attribute_service = AttributeService(
        schema_service, validation_service, sqlite_database_service, review_service
    )
    item_service = ItemService(
        attribute_service,
        TagService(sqlite_database_service),
        MapperService(
            attribute_service,
            validation_service,
            schema_service,
            sqlite_database_service,
            review_service,
        ),
        schema_service,
        validation_service,
        sqlite_database_service,
        review_service,
    )
    return _StoredProject(sqlite_database_service, item_service, schema)


@pytest.mark.integration
class TestLoadingMigrations:
    def test_a_migration_within_a_family_is_loaded(
        self, schema_service: SchemaService, schema: ExampleSchema
    ):
        assert schema_service.migration_of(schema.uid) is not None

    def test_a_migration_is_asked_for_from_the_previous_roots_only(
        self,
        decoy: Decoy,
        schema: ExampleSchema,
        other_schema: RootSchema,
        sqlite_database_service: DatabaseService,
    ):
        # Arrange
        schema_interface = decoy.mock(cls=SchemaInterface)
        decoy.when(schema_interface.root()).then_return(other_schema)
        decoy.when(schema_interface.previous_roots()).then_return([schema])

        # Act
        SchemaService(schema_interface, sqlite_database_service)

        # Assert
        decoy.verify(schema_interface.migration_from(schema), times=1)
        decoy.verify(schema_interface.migration_from(other_schema), times=0)

    def test_a_migration_to_another_family_is_loaded(
        self,
        migration: _SexMigration,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        stranger = other_schema.model_copy(update={"family_uid": uuid4()})

        # Act
        schema_service = schema_service_of(
            stranger, schema, migrations={schema.uid: migration}
        )

        # Assert
        assert schema_service.migration_of(schema.uid) is migration

    def test_an_application_without_migrations_migrates_nothing(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        schema_service = schema_service_of(schema, other_schema)

        assert schema_service.migration_of(schema.uid) is None
        assert schema_service.migrations == {}


@pytest.mark.integration
class TestMigratingAProject:
    @staticmethod
    def _plan(
        migration_service: MigrationService, stored: _StoredProject
    ) -> ProjectMigration:
        migration_service.create(stored.project.uid)
        migration_service.plan(stored.project.uid)
        return migration_service.get(stored.project.uid)

    @staticmethod
    def _resolved(migration_service: MigrationService, stored: _StoredProject) -> int:
        """Count the resolved or accepted attribute issues of the migration."""
        return sum(
            issue.resolved_at is not None
            for object_ in migration_service.get(stored.project.uid).issues
            for issue in object_.attribute_issues
        )

    @staticmethod
    def _sex(issue: AttributeMigrationIssue, sex: str | None) -> AnyAttribute | None:
        """The sex resolved for an issue of it, on the target schema."""
        if sex is None:
            return None
        return issue.original.model_copy(
            update={
                "schema_uid": issue.target_attribute_schema_uid,
                "original_value": None,
                "updated_value": sex,
                "mapped_value": None,
            }
        )

    @classmethod
    def _resolve_all(
        cls,
        migration_service: MigrationService,
        stored: _StoredProject,
        resolve: Callable[[AttributeMigrationIssue], AnyAttribute | None] | None = None,
    ) -> None:
        """Resolve every issue, by default the sex as female, and accept every
        dropped attribute."""
        planned = migration_service.get(stored.project.uid)
        for object_ in planned.issues:
            for issue in object_.attribute_issues:
                if issue.target_attribute_schema_uid is None:
                    attribute = None
                elif resolve is not None:
                    attribute = resolve(issue)
                else:
                    attribute = cls._sex(issue, "Female")
                migration_service.resolve(
                    stored.project.uid,
                    issue.uid,
                    attribute,
                )

    @classmethod
    def _migrate(
        cls,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
        resolve: Callable[[AttributeMigrationIssue], AnyAttribute | None] | None = None,
    ) -> None:
        """Start, plan, resolve every issue, submit, and complete."""
        cls._plan(migration_service, stored)
        cls._resolve_all(migration_service, stored, resolve)
        migration_service.submit(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            migration_service.complete(stored.project.uid, session=session)

    def test_planning_stores_attribute_issues_and_what_is_dropped_changing_nothing(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        item_service: ItemService,
        stored: _StoredProject,
        schema: ExampleSchema,
    ):
        # Arrange
        migration.dropped_tags = {"report"}

        # Act
        created = migration_service.create(stored.project.uid)
        migration_service.plan(stored.project.uid)
        planned = migration_service.get(stored.project.uid)

        # Assert
        assert created.status == MigrationStatus.PLANNING
        assert created.previous_project_status == ProjectStatus.IN_PROGRESS
        assert planned.status == MigrationStatus.CURATING
        assert planned.target_root_schema_uid == OTHER_ROOT_SCHEMA_UID
        assert [
            issue.resolved_at
            for object_ in planned.issues
            for issue in object_.attribute_issues
        ] == [None, None]
        objects = {object_.uid: object_ for object_ in planned.issues}
        assert objects.keys() == {stored.other_patient.uid, stored.observation.uid}
        other_patient = objects[stored.other_patient.uid]
        assert other_patient.kind == MigrationObjectKind.ITEM
        assert other_patient.identifier == "patient-2"
        assert other_patient.target_schema_uid == schema.patient_schema_uid
        [issue] = other_patient.attribute_issues
        assert issue.tag == "sex"
        assert issue.target_attribute_schema_uid == OTHER_SEX_SCHEMA_UID
        assert issue.original.original_value == "Other"
        assert issue.original.display_value is not None
        assert issue.proposed is not None
        assert issue.proposed.schema_uid == OTHER_SEX_SCHEMA_UID
        assert issue.proposed.value is None
        assert "Other" in issue.problem
        assert issue.resolved_at is None
        [dropped] = objects[stored.observation.uid].attribute_issues
        assert dropped.tag == "report"
        assert dropped.target_attribute_schema_uid is None
        assert dropped.original is not None
        assert dropped.original.display_value is not None
        assert dropped.proposed is None
        assert dropped.problem == (
            f"'{dropped.original.display_value}' of {dropped.display_name} is "
            f"dropped: it has no place in {planned.target_root_schema_name}."
        )
        assert dropped.resolved_at is None
        # Nothing of the project is changed.
        with sqlite_database_service.get_session() as session:
            project = session.get_one(DatabaseProject, stored.project.uid)
            assert project.root_schema_uid == schema.uid
            assert project.status == ProjectStatus.MIGRATING
        sex = item_service.get(stored.other_patient.uid).attributes["sex"]
        assert sex.schema_uid == schema.patient.attributes["sex"].uid

    def test_an_attribute_issue_is_resolved_on_its_attribute_schema(
        self,
        migration_service: MigrationService,
        stored: _StoredProject,
        schema: ExampleSchema,
    ):
        # Arrange
        planned = self._plan(migration_service, stored)
        [issue] = [
            issue for object_ in planned.issues for issue in object_.attribute_issues
        ]
        female = self._sex(issue, "Female")
        assert female is not None
        on_the_source = female.model_copy(
            update={"schema_uid": schema.patient.attributes["sex"].uid}
        )

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="attribute schema"):
            migration_service.resolve(
                stored.project.uid,
                issue.uid,
                on_the_source,
            )
        with pytest.raises(NotFoundError):
            migration_service.resolve(stored.project.uid, uuid4(), female)
        resolved = migration_service.resolve(stored.project.uid, issue.uid, female)
        assert resolved.resolved_at is not None
        assert resolved.resolved is not None
        assert resolved.resolved.value == "Female"
        assert self._resolved(migration_service, stored) == 1
        left_empty = migration_service.resolve(stored.project.uid, issue.uid, None)
        assert left_empty.resolved_at is not None
        assert left_empty.resolved is None

    def test_a_migration_is_not_submitted_while_an_attribute_issue_is_not_resolved(
        self,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        self._plan(migration_service, stored)

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="not resolved"):
            migration_service.submit(stored.project.uid)
        assert migration_service.get(stored.project.uid).status == (
            MigrationStatus.CURATING
        )

    def test_a_dropped_attribute_is_accepted_not_given_a_value(
        self,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
    ):
        # Arrange
        migration.dropped_tags = {"report"}
        planned = self._plan(migration_service, stored)
        [dropped] = [
            issue
            for object_ in planned.issues
            for issue in object_.attribute_issues
            if issue.target_attribute_schema_uid is None
        ]
        assert dropped.original is not None

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="dropped"):
            migration_service.resolve(
                stored.project.uid,
                dropped.uid,
                dropped.original,
            )
        accepted = migration_service.resolve(stored.project.uid, dropped.uid, None)
        assert accepted.resolved_at is not None
        assert accepted.resolved is None
        assert self._resolved(migration_service, stored) == 1

    def test_a_migration_is_not_submitted_until_a_dropped_attribute_is_accepted(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        # Arrange
        migration.dropped_tags = {"report"}
        planned = self._plan(migration_service, stored)
        for object_ in planned.issues:
            for issue in object_.attribute_issues:
                if issue.target_attribute_schema_uid is not None:
                    migration_service.resolve(
                        stored.project.uid,
                        issue.uid,
                        self._sex(issue, "Female"),
                    )

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="not resolved"):
            migration_service.submit(stored.project.uid)
        self._resolve_all(migration_service, stored)
        migration_service.submit(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            migration_service.complete(stored.project.uid, session=session)
        assert "report" not in item_service.get(stored.observation.uid).attributes

    def test_attribute_issues_are_resolved_only_while_curated(
        self,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        planned = self._plan(migration_service, stored)
        [issue] = [
            issue for object_ in planned.issues for issue in object_.attribute_issues
        ]
        self._resolve_all(migration_service, stored)
        submitted = migration_service.submit(stored.project.uid)

        # Act & Assert
        assert submitted.status == MigrationStatus.COMPLETING
        with pytest.raises(NotAllowedActionError, match="completing"):
            migration_service.resolve(stored.project.uid, issue.uid, None)
        with pytest.raises(NotAllowedActionError, match="completing"):
            migration_service.submit(stored.project.uid)

    def test_completing_puts_the_resolved_values_at_their_tags_and_restores_the_status(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            session.get_one(
                DatabaseProject, stored.project.uid
            ).status = ProjectStatus.COMPLETED

        # Act
        self._migrate(sqlite_database_service, migration_service, stored)

        # Assert
        with sqlite_database_service.get_session() as session:
            project = session.get_one(DatabaseProject, stored.project.uid)
            assert project.root_schema_uid == OTHER_ROOT_SCHEMA_UID
            assert project.status == ProjectStatus.COMPLETED
            assert session.scalars(select(DatabaseAttributeMigrationIssue)).all() == []
        other_patient = item_service.get(stored.other_patient.uid)
        sex = other_patient.attributes["sex"]
        assert sex.schema_uid == OTHER_SEX_SCHEMA_UID
        assert sex.value == "Female"
        assert sex.uid == stored.other_patient.attributes["sex"].uid
        assert other_patient.valid_attributes is True
        with pytest.raises(NotFoundError):
            migration_service.get(stored.project.uid)

    def test_a_tag_left_empty_is_unset(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        """And the item invalid where the attribute is required, flagged for
        review on the new root."""
        # Act
        self._migrate(
            sqlite_database_service,
            migration_service,
            stored,
            lambda issue: self._sex(issue, None),
        )

        # Assert
        other_patient = item_service.get(stored.other_patient.uid)
        assert "sex" not in other_patient.attributes
        assert other_patient.valid_attributes is False
        with sqlite_database_service.get_session() as session:
            assert session.scalars(
                select(DatabaseReviewIssue).where(
                    DatabaseReviewIssue.item_uid == stored.other_patient.uid
                )
            ).all()

    def test_a_private_attribute_is_resolved(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        # Arrange
        migration.unresolved_tags = {"report"}

        def resolve(issue: AttributeMigrationIssue) -> AnyAttribute | None:
            if issue.tag != "report":
                return self._sex(issue, "Male")
            assert issue.proposed is not None
            return issue.proposed.model_copy(update={"updated_value": "Malignant"})

        # Act
        self._migrate(sqlite_database_service, migration_service, stored, resolve)

        # Assert
        observation = item_service.get(stored.observation.uid)
        report = observation.private_attributes["report"]
        assert report.value == "Malignant"
        assert report.uid == stored.observation.private_attributes["report"].uid
        assert "report" not in observation.attributes

    def test_a_resolved_value_keeps_the_row_of_the_attribute_it_resolves(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        """Its uid, lock, and read only flag, whatever uid the value is sent
        with."""
        # Arrange
        other_sex = stored.other_patient.attributes["sex"].uid
        with sqlite_database_service.get_session() as session:
            row = session.get_one(DatabaseAttribute, other_sex)
            row.locked, row.read_only = True, True

        def resolve(issue: AttributeMigrationIssue) -> AnyAttribute | None:
            return EnumAttribute(
                uid=UUID(int=0),
                schema_uid=issue.target_attribute_schema_uid,
                updated_value="Female",
            )

        # Act
        self._migrate(sqlite_database_service, migration_service, stored, resolve)

        # Assert
        sex = item_service.get(stored.other_patient.uid).attributes["sex"]
        assert (sex.uid, sex.value) == (other_sex, "Female")
        with sqlite_database_service.get_session() as session:
            row = session.get_one(DatabaseAttribute, other_sex)
            assert (row.locked, row.read_only) == (True, True)

    def test_every_object_is_moved(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        # Act
        self._migrate(sqlite_database_service, migration_service, stored)

        # Assert
        with sqlite_database_service.get_session() as session:
            project = session.get_one(DatabaseProject, stored.project.uid)
            assert project.root_schema_uid == OTHER_ROOT_SCHEMA_UID
            assert project.status == ProjectStatus.IN_PROGRESS
        patient = item_service.get(stored.patient.uid)
        assert patient.attributes["sex"].schema_uid == OTHER_SEX_SCHEMA_UID
        assert patient.attributes["sex"].original_value == "Male"
        assert patient.attributes["sex"].updated_value == "Female"
        assert patient.attributes["sex"].uid == stored.patient.attributes["sex"].uid
        assert patient.valid_attributes is True
        slide = item_service.get(stored.slide.uid)
        staining = slide.attributes["staining"]
        before = stored.slide.attributes["staining"]
        assert staining.uid == before.uid
        assert staining.original_value == before.original_value
        observation = item_service.get(stored.observation.uid)
        assert observation.private_attributes["report"].original_value == "Benign"

    def test_the_locks_and_read_only_flags_of_attributes_are_kept(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """Also of an attribute resolved by the curator, which keeps its uid."""
        # Arrange
        sex = stored.patient.attributes["sex"].uid
        other_sex = stored.other_patient.attributes["sex"].uid
        staining = stored.slide.attributes["staining"].uid
        with sqlite_database_service.get_session() as session:
            session.get_one(DatabaseAttribute, sex).locked = True
            session.get_one(DatabaseAttribute, other_sex).locked = True
            session.get_one(DatabaseAttribute, staining).read_only = True

        # Act
        self._migrate(sqlite_database_service, migration_service, stored)

        # Assert
        with sqlite_database_service.get_session() as session:
            sex_row = session.get_one(DatabaseAttribute, sex)
            assert sex_row.schema_uid == OTHER_SEX_SCHEMA_UID
            assert (sex_row.locked, sex_row.read_only) == (True, False)
            other_sex_row = session.get_one(DatabaseAttribute, other_sex)
            assert other_sex_row.schema_uid == OTHER_SEX_SCHEMA_UID
            assert other_sex_row.locked is True
            staining_row = session.get_one(DatabaseAttribute, staining)
            assert (staining_row.locked, staining_row.read_only) == (False, True)

    def test_unmapped_values_are_recorded_again_on_the_target_schemas(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """They go with the rows they are of, which are written anew."""
        # Arrange
        sex = stored.patient.attributes["sex"].uid
        with sqlite_database_service.get_session() as session:
            row = session.get_one(DatabaseAttribute, sex)
            row.mappable_value = "man"
            sqlite_database_service.record_unmapped_values(row, session)

        # Act
        self._migrate(sqlite_database_service, migration_service, stored)

        # Assert
        with sqlite_database_service.get_session() as session:
            unmapped = session.scalars(
                select(DatabaseUnmappedValue).where(
                    DatabaseUnmappedValue.root_attribute_uid == sex
                )
            ).all()
            assert [(value.schema_uid, value.value) for value in unmapped] == [
                (OTHER_SEX_SCHEMA_UID, "man")
            ]

    def test_search_items_are_moved_where_the_migration_puts_them(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
        schema: ExampleSchema,
    ):
        """Also those of a search that failed, which left no item."""

        # Arrange
        migrate_item_schema = migration.migrate_item_schema

        def block_to_specimen(item_schema: ItemSchema) -> ItemSchema:
            if item_schema.uid == schema.block_schema_uid:
                item_schema = schema.samples[schema.specimen_schema_uid]
            return migrate_item_schema(item_schema)

        monkeypatch.setattr(migration, "migrate_item_schema", block_to_specimen)
        failed_uid, found_uid = self._add_search_items(
            sqlite_database_service, stored, schema
        )

        # Act
        self._migrate(sqlite_database_service, migration_service, stored)

        # Assert
        with sqlite_database_service.get_session() as session:
            failed = session.get_one(DatabaseMetadataSearchItem, failed_uid)
            assert failed.schema_uid == schema.specimen_schema_uid
            found = session.get_one(DatabaseMetadataSearchItem, found_uid)
            assert found.schema_uid == schema.patient_schema_uid

    @pytest.mark.parametrize("wrong", ["no item schema", "another kind"])
    def test_a_search_item_moved_off_the_target_item_schemas_is_refused(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
        schema: ExampleSchema,
        wrong: str,
    ):
        """When the migration is planned."""
        # Arrange
        target = (
            schema.samples[schema.block_schema_uid].model_copy(update={"uid": uuid4()})
            if wrong == "no item schema"
            else schema.images[schema.image_schema_uid]
        )
        monkeypatch.setattr(migration, "migrate_item_schema", lambda _: target)
        self._add_search_items(sqlite_database_service, stored, schema)
        migration_service.create(stored.project.uid)

        # Act & Assert
        with pytest.raises(MigrationError, match="search item"):
            migration_service.plan(stored.project.uid)
        assert migration_service.get(stored.project.uid).status == (
            MigrationStatus.PLANNING
        )

    @staticmethod
    def _add_search_items(
        sqlite_database_service: DatabaseService,
        stored: _StoredProject,
        schema: ExampleSchema,
    ) -> tuple[UUID, UUID]:
        """A search item of a block whose search failed, and one of the patient
        found."""
        with sqlite_database_service.get_session() as session:
            failed = DatabaseMetadataSearchItem(
                stored.batch_uid,
                "block-1",
                schema.block_schema_uid,
                status=MetadataImportStatus.FAILED,
            )
            found = DatabaseMetadataSearchItem(
                stored.batch_uid,
                "patient-1",
                schema.patient_schema_uid,
                status=MetadataImportStatus.COMPLETE,
                item_uid=stored.patient.uid,
            )
            session.add_all([failed, found])
            session.flush()
            return failed.uid, found.uid

    @pytest.mark.parametrize("breakage", ["wrong_kind", "wrong_tag"])
    def test_a_migration_off_the_target_schemas_is_refused(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
        breakage: str,
    ):
        """When planned, and when completed, with nothing changed."""
        # Arrange
        self._plan(migration_service, stored)
        self._resolve_all(migration_service, stored)
        migration_service.submit(stored.project.uid)
        setattr(migration, breakage, True)

        # Act & Assert
        with (
            pytest.raises(MigrationError),
            sqlite_database_service.get_session() as session,
        ):
            migration_service.complete(stored.project.uid, session=session)
        with sqlite_database_service.get_session() as session:
            project = session.get_one(DatabaseProject, stored.project.uid)
            assert project.root_schema_uid == ExampleSchema().uid
        migration_service.revert(stored.project.uid)
        migration_service.create(stored.project.uid)
        with pytest.raises(MigrationError):
            migration_service.plan(stored.project.uid)

    @pytest.mark.parametrize(
        ("wrong", "unresolved_tags"),
        [
            ("tag", set()),
            ("proposal", set()),
            ("private", {"report"}),
        ],
    )
    def test_an_unresolved_attribute_off_the_target_schema_is_refused(
        self,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
        wrong: str,
        unresolved_tags: set[str],
    ):
        """One under a tag the target schema does not have, one proposed on
        another attribute schema, and one among the private attributes."""
        # Arrange
        migration.unresolved_tags = unresolved_tags
        migration.wrong_unresolved = wrong
        migration_service.create(stored.project.uid)

        # Act & Assert
        with pytest.raises(MigrationError):
            migration_service.plan(stored.project.uid)

    @pytest.mark.parametrize("changed", ["unresolved_tags", "dropped_tags"])
    def test_completing_fails_where_the_migration_no_longer_matches_the_plan(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
        changed: str,
    ):
        """With nothing changed, and the migration left to be reverted: one
        now leaves unresolved, the other drops, what the plan has not."""
        # Arrange
        self._plan(migration_service, stored)
        self._resolve_all(migration_service, stored)
        migration_service.submit(stored.project.uid)
        setattr(migration, changed, {"report"})

        # Act
        complete_schema_migration.func.__wrapped__(  # type: ignore[attr-defined]
            stored.project.uid,
            migration_service=migration_service,
        )

        # Assert
        failed = migration_service.get(stored.project.uid)
        assert failed.status == MigrationStatus.FAILED
        assert failed.error is not None and "no longer" in failed.error
        with sqlite_database_service.get_session() as session:
            project = session.get_one(DatabaseProject, stored.project.uid)
            assert project.root_schema_uid == ExampleSchema().uid
            assert project.status == ProjectStatus.MIGRATING
        with pytest.raises(NotAllowedActionError):
            migration_service.submit(stored.project.uid)
        assert migration_service.revert(stored.project.uid).status == (
            ProjectStatus.IN_PROGRESS
        )

    def test_reverting_restores_the_status_and_removes_the_plan(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        schema_service: SchemaService,
        stored: _StoredProject,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            session.get_one(
                DatabaseProject, stored.project.uid
            ).status = ProjectStatus.COMPLETED
        self._plan(migration_service, stored)
        self._resolve_all(migration_service, stored)

        # Act
        project = migration_service.revert(stored.project.uid)

        # Assert
        assert project.status == ProjectStatus.COMPLETED
        assert project.root_schema_uid == ExampleSchema().uid
        with pytest.raises(NotFoundError):
            migration_service.get(stored.project.uid)
        with pytest.raises(NotFoundError):
            migration_service.revert(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            assert session.scalars(select(DatabaseAttributeMigrationIssue)).all() == []
        assert stored.can_migrate(sqlite_database_service, schema_service) is True

    def test_a_migration_reverted_before_it_is_planned_is_not_planned(
        self,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """Such as one whose planning task waited to be run."""
        # Arrange
        migration_service.create(stored.project.uid)
        migration_service.revert(stored.project.uid)

        # Act
        migration_service.plan(stored.project.uid)

        # Assert
        with pytest.raises(NotFoundError):
            migration_service.get(stored.project.uid)

    def test_a_migrating_project_is_not_migrated_again(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        migration_service.create(stored.project.uid)

        # Act & Assert
        assert stored.can_migrate(sqlite_database_service, schema_service) is False
        with pytest.raises(NotAllowedActionError):
            migration_service.create(stored.project.uid)

    def test_a_migration_is_refused_while_a_batch_is_busy(
        self,
        schema_service: SchemaService,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            batch = sqlite_database_service.get_batch(session, stored.batch_uid)
            batch.status = BatchStatus.METADATA_SEARCHING

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="being searched"):
            migration_service.create(stored.project.uid)
        assert stored.can_migrate(sqlite_database_service, schema_service) is False
        with pytest.raises(NotFoundError):
            migration_service.get(stored.project.uid)

    def test_the_planning_task_plans(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        migration_service.create(stored.project.uid)

        # Act
        plan_schema_migration.func.__wrapped__(  # type: ignore[attr-defined]
            str(stored.project.uid),
            migration_service=migration_service,
        )

        # Assert
        planned = migration_service.get(stored.project.uid)
        assert planned.status == MigrationStatus.CURATING
        assert sum(len(object_.attribute_issues) for object_ in planned.issues) == 1

    def test_the_completing_task_sets_the_project_back_to_its_status(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """A completed project stays completed, and is validated again."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            session.get_one(
                DatabaseProject, stored.project.uid
            ).status = ProjectStatus.COMPLETED
        self._plan(migration_service, stored)
        self._resolve_all(
            migration_service, stored, lambda issue: self._sex(issue, None)
        )
        migration_service.submit(stored.project.uid)

        # Act
        complete_schema_migration.func.__wrapped__(  # type: ignore[attr-defined]
            stored.project.uid,
            migration_service=migration_service,
        )

        # Assert
        with sqlite_database_service.get_session() as session:
            project = session.get_one(DatabaseProject, stored.project.uid)
            assert project.status == ProjectStatus.COMPLETED
            assert project.root_schema_uid == OTHER_ROOT_SCHEMA_UID
            other_patient = sqlite_database_service.get_item(
                session, stored.other_patient.uid
            )
            assert other_patient.valid_attributes is False

    def test_the_completing_task_fails_the_migration_and_changes_nothing(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
    ):
        # Arrange
        self._plan(migration_service, stored)
        self._resolve_all(migration_service, stored)
        migration_service.submit(stored.project.uid)
        migration.wrong_kind = True

        # Act
        complete_schema_migration.func.__wrapped__(  # type: ignore[attr-defined]
            stored.project.uid,
            migration_service=migration_service,
        )

        # Assert
        assert migration_service.get(stored.project.uid).status == (
            MigrationStatus.FAILED
        )
        with sqlite_database_service.get_session() as session:
            project = session.get_one(DatabaseProject, stored.project.uid)
            assert project.status == ProjectStatus.MIGRATING
            assert project.root_schema_uid == ExampleSchema().uid
            slide = sqlite_database_service.get_item(session, stored.slide.uid)
            assert slide.schema_uid == ExampleSchema().slide_schema_uid

    def test_the_actions_of_a_project_offer_migrating_it_as_its_rules_do(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        project_service = ProjectService(
            attribute_service=decoy.mock(cls=AttributeService),
            batch_service=decoy.mock(cls=BatchService),
            schema_service=schema_service,
            validation_service=validation_service,
            mapper_service=decoy.mock(cls=MapperService),
            database_service=sqlite_database_service,
            storage_service=decoy.mock(cls=StorageService),
        )
        before = project_service.get_actions(stored.project.uid)

        # Act
        migration_service.create(stored.project.uid)
        while_migrating = project_service.get_actions(stored.project.uid)

        # Assert
        assert before.has_migration is True
        assert before.migrate_refusal is None
        assert while_migrating.has_migration is True
        assert while_migrating.migrate_refusal == "the project is being migrated"
        assert stored.can_migrate(sqlite_database_service, schema_service) is False
        assert not any(
            while_migrating.model_dump(
                exclude={"has_migration", "migrate_refusal"}
            ).values()
        )

    def test_a_migrating_project_cannot_be_deleted(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        project_service = ProjectService(
            attribute_service=decoy.mock(cls=AttributeService),
            batch_service=decoy.mock(cls=BatchService),
            schema_service=schema_service,
            validation_service=validation_service,
            mapper_service=decoy.mock(cls=MapperService),
            database_service=sqlite_database_service,
            storage_service=decoy.mock(cls=StorageService),
        )
        migration_service.create(stored.project.uid)

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="being migrated"):
            project_service.set_as_deleting(stored.project.uid)

    def test_a_migrating_project_cannot_be_changed(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        schema_service: SchemaService,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        # Arrange
        assert stored.can_migrate(sqlite_database_service, schema_service) is True
        migration_service.create(stored.project.uid)

        # Act & Assert
        with pytest.raises(ProjectNotEditableError, match="being migrated"):
            item_service.select(stored.slide.uid, ItemSelect(select=False))
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, stored.project.uid)
            assert schema_service.support_of(project).change_refusal == (
                "the project is being migrated"
            )

    @pytest.mark.parametrize("taken_back_into_progress", [False, True])
    def test_an_exported_project_is_not_migrated(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        migration_service: MigrationService,
        stored: _StoredProject,
        taken_back_into_progress: bool,
    ):
        """It keeps the schema it was exported with, whatever its status says
        after."""
        # Arrange
        project_service = ProjectService(
            attribute_service=decoy.mock(cls=AttributeService),
            batch_service=decoy.mock(cls=BatchService),
            schema_service=schema_service,
            validation_service=validation_service,
            mapper_service=decoy.mock(cls=MapperService),
            database_service=sqlite_database_service,
            storage_service=decoy.mock(cls=StorageService),
        )
        assert stored.can_migrate(sqlite_database_service, schema_service) is True
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, stored.project.uid)
            project.status = ProjectStatus.EXPORTING
        project_service.set_as_export_complete(stored.project.uid)
        if taken_back_into_progress:
            project_service.set_as_in_progress(stored.project.uid)

        # Act & Assert
        assert stored.can_migrate(sqlite_database_service, schema_service) is False
        with pytest.raises(NotAllowedActionError, match="has been exported"):
            migration_service.create(stored.project.uid)

    def test_a_project_exported_while_waiting_to_be_planned_is_not(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """The task checks again."""
        # Arrange
        migration_service.create(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, stored.project.uid)
            project.exported = datetime.datetime(2026, 1, 2)

        # Act & Assert
        with pytest.raises(NotAllowedActionError, match="has been exported"):
            migration_service.plan(stored.project.uid)

    def test_a_project_with_a_search_item_not_yet_searched_is_busy(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        migration_service: MigrationService,
        stored: _StoredProject,
        schema: ExampleSchema,
    ):
        """A retried search runs on a batch whose search is complete, and would
        write into what the migration moves."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            batch = sqlite_database_service.get_batch(session, stored.batch_uid)
            batch.status = BatchStatus.METADATA_SEARCH_COMPLETE
            session.add(
                DatabaseMetadataSearchItem(
                    stored.batch_uid, "patient-3", schema.patient_schema_uid
                )
            )

        # Act & Assert
        assert stored.can_migrate(sqlite_database_service, schema_service) is False
        with pytest.raises(NotAllowedActionError, match="being searched"):
            migration_service.create(stored.project.uid)

    @pytest.mark.parametrize(
        ("status", "migratable"),
        [
            (BatchStatus.IMAGE_POST_PROCESSING_COMPLETE, True),
            (BatchStatus.LOCKED, False),
            (BatchStatus.COMPLETED, False),
        ],
    )
    def test_a_project_with_images_stored_is_not_migrated(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        stored: _StoredProject,
        status: BatchStatus,
        migratable: bool,
    ):
        """What is written into the images is written when they are stored:
        processed images are not yet, a locked batch holds what goes into its
        bundle, and stored images carry the metadata of the old schema."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            batch = sqlite_database_service.get_batch(session, stored.batch_uid)
            batch.status = status

        # Act
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, stored.project.uid)
            reason = schema_service.support_of(project).migrate_refusal(
                DatabaseService.has_stored_batches(session, project),
                DatabaseService.has_busy_batches(session, project),
            )

        # Assert
        if migratable:
            assert reason is None
        else:
            assert reason is not None and "stored" in reason


GRADE_SCHEMA_UID = UUID("7e3f1b2a-5c4d-4e6f-8a9b-0c1d2e3f4a5b")


@pytest.mark.integration
class TestMigratingIntoNewRequirements:
    """The second root with a grade the case requires, which the example root
    does not have."""

    @pytest.fixture()
    def reviewed_other_schema(
        self, other_schema: RootSchema, schema: ExampleSchema
    ) -> RootSchema:
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

    @staticmethod
    def _issues(
        migration_service: MigrationService, stored: _StoredProject
    ) -> dict[tuple[str, str], AttributeMigrationIssue]:
        """The issues of the planned migration, by identifier and tag."""
        migration_service.create(stored.project.uid)
        migration_service.plan(stored.project.uid)
        planned = migration_service.get(stored.project.uid)
        return {
            (object_.identifier, issue.tag): issue
            for object_ in planned.issues
            for issue in object_.attribute_issues
        }

    def test_a_newly_required_attribute_is_an_attribute_issue(
        self,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Act
        issues = self._issues(migration_service, stored)

        # Assert
        grade = issues[("case-1", "grade")]
        assert grade.target_attribute_schema_uid == GRADE_SCHEMA_UID
        assert grade.original is None
        assert grade.proposed is None
        assert grade.problem == f"Required in {ExampleSchema().name} 2, has no value."

    def test_an_attribute_invalid_before_is_not_an_attribute_issue(
        self,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """The submitter of the project and the diagnose of the observation
        are required on both roots, and not set."""
        # Act
        issues = self._issues(migration_service, stored)

        # Assert
        assert set(issues) == {("case-1", "grade"), ("patient-2", "sex")}

    def test_a_newly_required_attribute_is_resolved(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        # Arrange
        issues = self._issues(migration_service, stored)
        resolutions: dict[tuple[str, str], AnyAttribute | None] = {
            ("case-1", "grade"): StringAttribute(
                uid=UUID(int=0), schema_uid=GRADE_SCHEMA_UID, updated_value="High"
            ),
            ("patient-2", "sex"): None,
        }
        for key, issue in issues.items():
            migration_service.resolve(
                stored.project.uid,
                issue.uid,
                resolutions[key],
            )
        migration_service.submit(stored.project.uid)

        # Act
        with sqlite_database_service.get_session() as session:
            migration_service.complete(stored.project.uid, session=session)

        # Assert
        case = item_service.get(stored.case.uid)
        assert case.attributes["grade"].value == "High"
        assert case.valid_attributes is True


@pytest.mark.integration
class TestMigratingMappers:
    @pytest.fixture()
    def original(
        self,
        sqlite_database_service: DatabaseService,
        mapper_service: MapperService,
        schema: ExampleSchema,
    ) -> UUID:
        """A mapper of the example sex, in a group, mapping "man" to "M"."""
        sex = schema.patient.attributes["sex"].uid
        mapper = mapper_service.get_or_create_mapper("sex", sex)
        with sqlite_database_service.get_session() as session:
            mapping = sqlite_database_service.add_mapping(
                session,
                mapper.uid,
                "^man$",
                EnumAttribute(uid=uuid4(), schema_uid=sex, original_value="M"),
            )
            mapping.hits = 7
            sqlite_database_service.add_mapping(
                session,
                mapper.uid,
                "^other$",
                EnumAttribute(uid=uuid4(), schema_uid=sex, original_value="Other"),
            )
        group = mapper_service.get_or_create_mapper_group("group", True)
        mapper_service.add_mappers_to_group(group, [mapper])
        return mapper.uid

    @staticmethod
    def set_up_mappers(
        schema_service: SchemaService,
        sqlite_database_service: DatabaseService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
        mapper_injector: MapperInjectorInterface | None = None,
    ) -> None:
        """Set up the mappers as `slidetap-mappers set-up` does."""
        mapper_service = MapperService(
            attribute_service,
            validation_service,
            schema_service,
            sqlite_database_service,
            review_service,
            mapper_injector,
        )
        migration_service = MigrationService(
            schema_service,
            sqlite_database_service,
            attribute_service,
            validation_service,
            review_service,
            mapper_service,
        )
        MapperSetUp(mapper_service, migration_service).run()

    def test_a_mapper_is_not_migrated_where_the_service_is_only_created(
        self,
        sqlite_database_service: DatabaseService,
        mapper_service: MapperService,
        original: UUID,
        schema: ExampleSchema,
    ):
        """As in the web app and a worker, which leave the mappers to
        `slidetap-mappers set-up`."""
        # Act
        with sqlite_database_service.get_session() as session:
            mapper = sqlite_database_service.get_mapper(session, original)

            # Assert
            assert mapper.attribute_schema_uid == schema.patient.attributes["sex"].uid

    def test_a_mapper_of_a_changed_attribute_is_migrated(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        original: UUID,
    ):
        # Act
        for _ in range(2):
            migration_service.migrate_mappers()

        # Assert
        self.assert_moved(sqlite_database_service, original)

    def test_a_mapper_is_migrated_before_the_sheet_of_the_target_is_injected(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
        original: UUID,
    ):
        """A sheet of the target root names the mapper, which would otherwise
        be migrated to it by its name, without its mapping items migrated."""

        # Arrange
        class _TargetSheet(MapperInjectorInterface):
            def inject(self):
                mapper = Mapper(
                    uid=uuid4(),
                    name="sex",
                    attribute_schema_uid=OTHER_SEX_SCHEMA_UID,
                    root_attribute_schema_uid=OTHER_SEX_SCHEMA_UID,
                )
                group = MapperGroup(
                    uid=uuid4(), name="group", mappers=[], default_enabled=True
                )
                return [(group, [(mapper, [])])]

        # Act
        self.set_up_mappers(
            schema_service,
            sqlite_database_service,
            attribute_service,
            validation_service,
            review_service,
            _TargetSheet(),
        )

        # Assert
        self.assert_moved(sqlite_database_service, original)

    def test_a_mapper_the_migration_fails_on_is_named(
        self,
        monkeypatch: pytest.MonkeyPatch,
        migration_service: MigrationService,
        migration: _SexMigration,
        original: UUID,
    ):
        # Arrange
        def broken(attribute: AnyAttribute) -> AnyAttribute | None:
            raise RuntimeError("broken")

        monkeypatch.setattr(migration, "migrate_attribute", broken)

        # Act & Assert
        with pytest.raises(ValueError, match="Mapper 'sex'"):
            migration_service.migrate_mappers()

    def test_a_mapper_migrated_to_another_family_is_given_that_family(
        self,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        other_schema: RootSchema,
        migration: _SexMigration,
        schema_service_of: Callable[..., SchemaService],
        original: UUID,
    ):
        # Arrange
        stranger = other_schema.model_copy(update={"family_uid": uuid4()})

        # Act
        self.migrate_mappers_to_stranger(
            sqlite_database_service, schema, stranger, migration, schema_service_of
        )

        # Assert
        self.assert_moved(sqlite_database_service, original)
        with sqlite_database_service.get_session() as session:
            mapper = sqlite_database_service.get_mapper(session, original)
            assert mapper.family_uid == stranger.family_uid

    def test_a_mapper_migrated_onto_a_name_taken_in_the_family_is_named(
        self,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        other_schema: RootSchema,
        migration: _SexMigration,
        schema_service_of: Callable[..., SchemaService],
        original: UUID,
    ):
        # Arrange
        stranger = other_schema.model_copy(update={"family_uid": uuid4()})
        with sqlite_database_service.get_session() as session:
            taken = uuid4()
            sqlite_database_service.add_mapper(
                session, "sex", taken, taken, family_uid=stranger.family_uid
            )

        # Act & Assert
        with pytest.raises(ValueError, match="Mapper 'sex'"):
            self.migrate_mappers_to_stranger(
                sqlite_database_service, schema, stranger, migration, schema_service_of
            )

    @staticmethod
    def migrate_mappers_to_stranger(
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        stranger: RootSchema,
        migration: _SexMigration,
        schema_service_of: Callable[..., SchemaService],
    ) -> None:
        """Migrate the mappers where the root of new projects is of another
        family than the root migrated from."""
        schema_service = schema_service_of(
            stranger, schema, migrations={schema.uid: migration}
        )
        validation_service = ValidationService(schema_service, sqlite_database_service)
        review_service = ReviewService(
            schema_service, validation_service, sqlite_database_service
        )
        attribute_service = AttributeService(
            schema_service, validation_service, sqlite_database_service, review_service
        )
        mapper_service = MapperService(
            attribute_service,
            validation_service,
            schema_service,
            sqlite_database_service,
            review_service,
        )
        MigrationService(
            schema_service,
            sqlite_database_service,
            attribute_service,
            validation_service,
            review_service,
            mapper_service,
        ).migrate_mappers()

    @staticmethod
    def assert_moved(sqlite_database_service: DatabaseService, original: UUID):
        with sqlite_database_service.get_session() as session:
            mappers = session.scalars(select(DatabaseMapper)).all()
            assert [mapper.uid for mapper in mappers] == [original]
            mapper = mappers[0]
            assert mapper.name == "sex"
            assert mapper.attribute_schema_uid == OTHER_SEX_SCHEMA_UID
            assert mapper.root_attribute_schema_uid == OTHER_SEX_SCHEMA_UID
            mappings = session.scalars(
                select(DatabaseMappingItem).where(
                    DatabaseMappingItem.mapper_uid == original
                )
            ).all()
            # "Other" has no sex in the second root, and is removed.
            assert [
                (
                    mapping.expression,
                    mapping.attribute.schema_uid,
                    mapping.attribute.original_value,
                    mapping.hits,
                )
                for mapping in mappings
            ] == [("^man$", OTHER_SEX_SCHEMA_UID, "Male", 7)]
            groups = list(sqlite_database_service.get_mapper_groups(session))
            assert {mapper.uid for mapper in groups[0].mappers} == {original}


@pytest.mark.unittest
class TestAttributeMigrator:
    def test_nested_attributes_are_migrated_and_the_mapping_kept(
        self, schema: ExampleSchema
    ):
        # Arrange
        staining = schema.slide.attributes["staining"]
        moved_to = staining.model_copy(
            update={
                "uid": uuid4(),
                "attribute": staining.attribute.model_copy(  # type: ignore
                    update={"uid": uuid4()}
                ),
            }
        )
        attribute = ListAttribute(
            uid=uuid4(),
            schema_uid=staining.uid,
            mapping_item_uid=uuid4(),
            original_value=[
                CodeAttribute(
                    uid=uuid4(),
                    schema_uid=staining.attribute.uid,  # type: ignore
                    original_value=Code(code="HE", scheme="scheme", meaning="HE"),
                )
            ],
        )

        # Act
        migrated = UnchangedAttributeMigrator().migrate(attribute, moved_to).attribute

        # Assert
        assert migrated.uid == attribute.uid
        assert migrated.schema_uid == moved_to.uid
        assert migrated.mapping_item_uid == attribute.mapping_item_uid
        assert migrated.original_value is not None
        assert migrated.original_value[0].schema_uid == moved_to.attribute.uid
        assert attribute.original_value is not None
        assert attribute.original_value[0].schema_uid == staining.attribute.uid  # type: ignore

    def test_another_value_type_is_refused(self, schema: ExampleSchema):
        attribute = StringAttribute(uid=uuid4(), schema_uid=uuid4())

        with pytest.raises(ValueError):
            UnchangedAttributeMigrator().migrate(
                attribute, schema.patient.attributes["sex"]
            )

    def test_removed_mapping_items_are_referred_to_by_nothing(self):
        """Nested in a value as well as at the top."""
        # Arrange
        removed, kept = uuid4(), uuid4()
        attribute = ListAttribute(
            uid=uuid4(),
            schema_uid=uuid4(),
            mapping_item_uid=removed,
            original_value=[
                StringAttribute(
                    uid=uuid4(),
                    schema_uid=uuid4(),
                    mapping_item_uid=mapping_item_uid,
                    mapped_value="mapped",
                )
                for mapping_item_uid in (removed, kept)
            ],
        )

        # Act
        cleared = UnchangedAttributeMigrator.without_mapping_items(
            attribute, lambda uid: uid == removed
        )

        # Assert
        assert cleared.mapping_item_uid is None
        assert cleared.original_value is not None
        assert [nested.mapping_item_uid for nested in cleared.original_value] == [
            None,
            kept,
        ]
        assert [nested.mapped_value for nested in cleared.original_value] == [
            "mapped",
            "mapped",
        ]
