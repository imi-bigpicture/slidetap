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
"Unknown", under another uid. The migration converts the sex, drops one that
has no counterpart, and moves every other attribute as it is.

Against a real SQLite database: what is checked is what is saved.
"""

import datetime
import logging
from collections.abc import Callable, Mapping, Sequence
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from dishka import Container
from slidetap_example import ExampleSchema
from sqlalchemy import select

from slidetap.database import (
    DatabaseAttribute,
    DatabaseMapper,
    DatabaseMappingItem,
    DatabaseMetadataSearchItem,
    DatabaseProject,
    DatabaseReviewIssue,
    DatabaseUnmappedValue,
)
from slidetap.external_interfaces import (
    AttributeMigrator,
    MapperInjectorInterface,
    MigratedObject,
    SchemaMigration,
    SchemaMigrationInterface,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
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
    NotAllowedActionError,
    Observation,
    Project,
    ProjectNotEditableError,
    ProjectStatus,
    ReviewLayout,
    ReviewUnitSchema,
    RootSchema,
    Sample,
    StringAttribute,
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
from slidetap.task.tasks import process_schema_migration
from tests.conftest import OTHER_ROOT_SCHEMA_UID, OTHER_SEX_SCHEMA_UID

SEXES = {"M": "Male", "F": "Female"}
"""The sexes of the example root with one in the second; the rest have none."""


class _SexMigration(SchemaMigration):
    """Moves projects from the example root to the second, converting the sex
    of the patient value by value, and leaving out one with no counterpart.

    What it does wrong, where a test asks it to, is what the migration service
    has to refuse.
    """

    def __init__(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        wrong_kind: bool = False,
        wrong_tag: bool = False,
    ):
        self._schema = schema
        self._other_schema = other_schema
        self._migrator = AttributeMigrator()
        self._wrong_kind = wrong_kind
        self._wrong_tag = wrong_tag
        self.source = schema.uid
        self.target = OTHER_ROOT_SCHEMA_UID

    @property
    def source_root_uid(self) -> UUID:
        return self.source

    @property
    def target_root_uid(self) -> UUID:
        return self.target

    def migrate_project(self, project: Project) -> MigratedObject:
        return self._move(
            self._other_schema.project.uid,
            project.attributes,
            project.private_attributes,
            self._other_schema.project.attributes,
            self._other_schema.project.private_attributes,
        )

    def migrate_dataset(self, dataset: Dataset) -> MigratedObject:
        return self._move(
            self._other_schema.dataset.uid,
            dataset.attributes,
            dataset.private_attributes,
            self._other_schema.dataset.attributes,
            self._other_schema.dataset.private_attributes,
        )

    def migrate_item(self, item: Item) -> MigratedObject:
        schema_uid = item.schema_uid
        if self._wrong_kind and schema_uid == self._schema.slide_schema_uid:
            schema_uid = self._schema.image_schema_uid
        target: ItemSchema = {
            **self._other_schema.samples,
            **self._other_schema.images,
            **self._other_schema.observations,
            **self._other_schema.annotations,
        }[item.schema_uid]
        return self._move(
            schema_uid,
            item.attributes,
            item.private_attributes,
            target.attributes,
            target.private_attributes,
        )

    def _move(
        self,
        schema_uid: UUID,
        attributes: Mapping[str, AnyAttribute],
        private_attributes: Mapping[str, AnyAttribute],
        targets: Mapping[str, AttributeSchema],
        private_targets: Mapping[str, AttributeSchema],
    ) -> MigratedObject:
        return MigratedObject(
            schema_uid=schema_uid,
            attributes=self._move_attributes(attributes, targets),
            private_attributes=self._move_attributes(
                private_attributes, private_targets
            ),
        )

    def _move_attributes(
        self,
        attributes: Mapping[str, AnyAttribute],
        targets: Mapping[str, AttributeSchema],
    ) -> dict[str, AnyAttribute]:
        moved: dict[str, AnyAttribute] = {}
        for tag, attribute in attributes.items():
            converted = self.migrate_attribute(attribute)
            if converted is None:
                converted = self._migrator.migrate(attribute, targets[tag])
            elif converted.value is None:
                continue
            moved[f"{tag}-wrong" if self._wrong_tag else tag] = converted
        return moved

    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        if attribute.schema_uid != self._schema.patient.attributes["sex"].uid:
            return None
        return attribute.model_copy(
            update={
                "schema_uid": OTHER_SEX_SCHEMA_UID,
                "original_value": SEXES.get(attribute.original_value or ""),
                "updated_value": SEXES.get(attribute.updated_value or ""),
                "mapped_value": SEXES.get(attribute.mapped_value or ""),
            }
        )


class _Migrations(SchemaMigrationInterface):
    def __init__(self, *migrations: SchemaMigration):
        self._migrations = migrations

    @property
    def migrations(self) -> Sequence[SchemaMigration]:
        return self._migrations


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
def source_is_root() -> bool:
    """Whether the root migrated from is the root of new projects, rather
    than the root migrated to, as it is after an upgrade."""
    return False


@pytest.fixture()
def schema_service(
    schema: ExampleSchema,
    reviewed_other_schema: RootSchema,
    migration: "_SexMigration",
    schema_service_of: Callable[..., SchemaService],
    source_is_root: bool,
) -> SchemaService:
    if source_is_root:
        return schema_service_of(schema, reviewed_other_schema, migrations=[migration])
    return schema_service_of(reviewed_other_schema, schema, migrations=[migration])


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
) -> MigrationService:
    return MigrationService(
        schema_service,
        sqlite_database_service,
        attribute_service,
        validation_service,
        review_service,
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
        case = item_service.add(
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
                sample=(schema.case_schema_uid, case.uid),
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
            return schema_service.support_of(project).can_migrate

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

    @pytest.mark.parametrize(
        "breakage",
        [
            "source not provided",
            "target not provided",
            "same root",
            "two from one",
            "cycle",
        ],
    )
    def test_a_migration_between_roots_it_cannot_move_between_is_refused(
        self,
        migration: _SexMigration,
        schema: ExampleSchema,
        other_schema: RootSchema,
        breakage: str,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        migrations: list[SchemaMigration] = [migration]
        if breakage == "source not provided":
            migration.source = uuid4()
        elif breakage == "target not provided":
            migration.target = uuid4()
        elif breakage == "same root":
            migration.target = schema.uid
        elif breakage == "two from one":
            migrations.append(_SexMigration(schema, other_schema))
        else:
            back = _SexMigration(schema, other_schema)
            back.source, back.target = OTHER_ROOT_SCHEMA_UID, schema.uid
            migrations.append(back)

        # Act & Assert
        with pytest.raises(ValueError):
            schema_service_of(schema, other_schema, migrations=migrations)

    def test_a_migration_to_another_family_is_refused(
        self,
        migration: _SexMigration,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        stranger = other_schema.model_copy(
            update={"uid": uuid4(), "family_uid": uuid4()}
        )
        migration.target = stranger.uid

        # Act & Assert
        with pytest.raises(ValueError):
            schema_service_of(schema, other_schema, stranger, migrations=[migration])

    def test_roots_migrated_from_and_to_as_they_should_not_be_are_warned_of(
        self,
        migration: _SexMigration,
        schema: ExampleSchema,
        other_schema: RootSchema,
        caplog: pytest.LogCaptureFixture,
        schema_service_of: Callable[..., SchemaService],
    ):
        """A root migrated from that can still be edited has its mappers moved
        away, and one migrated to that cannot be edited leaves what a migration
        drops or leaves invalid to nobody."""
        # Act
        with caplog.at_level(logging.WARNING):
            schema_service_of(schema, other_schema, migrations=[migration])

        # Assert
        assert "can still be edited" in caplog.text
        assert "cannot be edited" in caplog.text

    def test_an_application_without_migrations_migrates_nothing(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        schema_service = schema_service_of(schema, other_schema)

        assert schema_service.migration_of(schema.uid) is None
        assert schema_service.migrations == []


@pytest.mark.integration
class TestMigratingAProject:
    def test_the_dry_run_saves_nothing_and_reports_what_the_migration_leaves(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        schema_service: SchemaService,
        stored: _StoredProject,
    ):
        # Act
        dry_run = migration_service.dry_run(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            unchanged = sqlite_database_service.get_project(
                session, stored.project.uid
            ).root_schema_uid
        migration_service.start(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            result = migration_service.migrate(stored.project.uid, session=session)

        # Assert
        assert unchanged == ExampleSchema().uid
        assert dry_run == result
        assert result.items == 5
        changes = {change.attribute_schema_uid: change for change in result.attributes}
        example_sex = ExampleSchema().patient.attributes["sex"].uid
        assert changes[example_sex].dropped == 1
        assert changes[OTHER_SEX_SCHEMA_UID].invalid == 1
        # A private attribute with a value is not invalid, though private
        # attributes are not validated.
        report = ExampleSchema().observation.private_attributes["report"]
        assert report.uid not in changes
        # What the dry run reported as invalid is what the migration left so:
        # attributes found invalid, and required ones without a value.
        left_invalid: dict[UUID, int] = {}
        target = schema_service.get_root(OTHER_ROOT_SCHEMA_UID)
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, stored.project.uid)
            dataset = sqlite_database_service.get_dataset(session, project.dataset_uid)
            owners = [
                (project, target.project),
                (dataset, target.dataset),
                *(
                    (item, target.get_item(item.schema_uid))
                    for item in sqlite_database_service.get_items_in_dataset(
                        session, dataset.uid
                    )
                ),
            ]
            for owner, owner_schema in owners:
                for row in owner.attributes:
                    if not row.valid:
                        left_invalid[row.schema_uid] = (
                            left_invalid.get(row.schema_uid, 0) + 1
                        )
                for rows, schemas in (
                    (owner.attributes, owner_schema.attributes),
                    (owner.private_attributes, owner_schema.private_attributes),
                ):
                    held = {row.tag for row in rows if row.model.value is not None}
                    for tag, attribute_schema in schemas.items():
                        if attribute_schema.optional or tag in held:
                            continue
                        if any(row.tag == tag for row in owner.attributes) and (
                            schemas is owner_schema.attributes
                        ):
                            # A row that is there was validated, and counted.
                            continue
                        left_invalid[attribute_schema.uid] = (
                            left_invalid.get(attribute_schema.uid, 0) + 1
                        )
        assert {
            change.attribute_schema_uid: change.invalid
            for change in dry_run.attributes
            if change.invalid
        } == left_invalid

    def test_every_object_is_moved(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        item_service: ItemService,
        stored: _StoredProject,
    ):
        # Act
        migration_service.start(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            migration_service.migrate(stored.project.uid, session=session)

        # Assert
        with sqlite_database_service.get_session() as session:
            project = session.get(DatabaseProject, stored.project.uid)
            assert project is not None
            assert project.root_schema_uid == OTHER_ROOT_SCHEMA_UID
            assert project.status == ProjectStatus.IN_PROGRESS
        patient = item_service.get(stored.patient.uid)
        assert patient.attributes["sex"].schema_uid == OTHER_SEX_SCHEMA_UID
        assert patient.attributes["sex"].original_value == "Male"
        assert patient.attributes["sex"].updated_value == "Female"
        assert patient.attributes["sex"].uid == stored.patient.attributes["sex"].uid
        assert patient.valid_attributes is True
        other_patient = item_service.get(stored.other_patient.uid)
        assert "sex" not in other_patient.attributes
        assert other_patient.valid_attributes is False
        slide = item_service.get(stored.slide.uid)
        staining = slide.attributes["staining"]
        before = stored.slide.attributes["staining"]
        assert staining.uid == before.uid
        assert staining.original_value == before.original_value
        observation = item_service.get(stored.observation.uid)
        assert observation.private_attributes["report"].original_value == "Benign"
        # The patient left invalid is flagged for review on the new root.
        with sqlite_database_service.get_session() as session:
            assert session.scalars(
                select(DatabaseReviewIssue).where(
                    DatabaseReviewIssue.item_uid == stored.other_patient.uid
                )
            ).all()

    def test_the_locks_and_read_only_flags_of_attributes_are_kept(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        sex = stored.patient.attributes["sex"].uid
        staining = stored.slide.attributes["staining"].uid
        with sqlite_database_service.get_session() as session:
            session.get_one(DatabaseAttribute, sex).locked = True
            session.get_one(DatabaseAttribute, staining).read_only = True

        # Act
        migration_service.start(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            migration_service.migrate(stored.project.uid, session=session)

        # Assert
        with sqlite_database_service.get_session() as session:
            sex_row = session.get_one(DatabaseAttribute, sex)
            assert sex_row.schema_uid == OTHER_SEX_SCHEMA_UID
            assert (sex_row.locked, sex_row.read_only) == (True, False)
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
        migration_service.start(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            migration_service.migrate(stored.project.uid, session=session)

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

    def test_search_items_are_moved_also_of_schemas_no_item_is_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
        schema: ExampleSchema,
    ):
        """A search that failed left no item, and its search item is moved
        where the migration puts an item of its schema."""
        # Arrange
        migrate_item = migration.migrate_item

        def block_to_specimen(item: Item) -> MigratedObject:
            if item.schema_uid != schema.block_schema_uid:
                return migrate_item(item)
            return MigratedObject(schema_uid=schema.specimen_schema_uid)

        monkeypatch.setattr(migration, "migrate_item", block_to_specimen)
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
            failed_uid, found_uid = failed.uid, found.uid

        # Act
        migration_service.start(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            migration_service.migrate(stored.project.uid, session=session)

        # Assert
        with sqlite_database_service.get_session() as session:
            failed = session.get_one(DatabaseMetadataSearchItem, failed_uid)
            assert failed.schema_uid == schema.specimen_schema_uid
            found = session.get_one(DatabaseMetadataSearchItem, found_uid)
            assert found.schema_uid == schema.patient_schema_uid

    @pytest.mark.parametrize("breakage", ["wrong_kind", "wrong_tag"])
    def test_a_migration_off_the_target_schemas_is_refused(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
        breakage: str,
    ):
        # Arrange
        setattr(migration, f"_{breakage}", True)

        # Act & Assert
        with pytest.raises(MigrationError):
            migration_service.dry_run(stored.project.uid)
        migration_service.start(stored.project.uid)
        with (
            pytest.raises(MigrationError),
            sqlite_database_service.get_session() as session,
        ):
            migration_service.migrate(stored.project.uid, session=session)
        with sqlite_database_service.get_session() as session:
            project = session.get(DatabaseProject, stored.project.uid)
            assert project is not None
            assert project.root_schema_uid == ExampleSchema().uid

    def test_a_migrating_project_is_not_migrated_again(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        migration_service.start(stored.project.uid)

        # Act & Assert
        assert stored.can_migrate(sqlite_database_service, schema_service) is False
        with pytest.raises(NotAllowedActionError):
            migration_service.start(stored.project.uid)

    def test_the_dry_run_is_refused_where_migrating_would_be(
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
            migration_service.dry_run(stored.project.uid)
        assert stored.can_migrate(sqlite_database_service, schema_service) is False

    def test_a_project_no_longer_migrating_is_not_migrated(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """Such as one reset while its task waited to be run."""
        # Act
        with sqlite_database_service.get_session() as session:
            report = migration_service.migrate(stored.project.uid, session=session)

        # Assert
        assert report is None
        with sqlite_database_service.get_session() as session:
            project = session.get(DatabaseProject, stored.project.uid)
            assert project is not None
            assert project.root_schema_uid == ExampleSchema().uid

    def test_a_stuck_migrating_project_is_reset(
        self,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        migration_service.start(stored.project.uid)

        # Act
        project = migration_service.reset(stored.project.uid)

        # Assert
        assert project.status == ProjectStatus.IN_PROGRESS
        with pytest.raises(NotAllowedActionError):
            migration_service.reset(stored.project.uid)

    def test_the_task_sets_the_project_back_where_the_service_cannot_be_created(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        # Arrange
        migration_service.start(stored.project.uid)
        container = decoy.mock(cls=Container)
        decoy.when(container.get(MigrationService)).then_raise(RuntimeError("broken"))

        # Act
        process_schema_migration.func.__wrapped__(  # type: ignore[attr-defined]
            stored.project.uid,
            ProjectStatus.COMPLETED.value,
            database_service=sqlite_database_service,
            container=container,
        )

        # Assert
        with sqlite_database_service.get_session() as session:
            project = session.get(DatabaseProject, stored.project.uid)
            assert project is not None
            assert project.status == ProjectStatus.COMPLETED

    def test_the_task_sets_the_project_back_where_the_migration_fails(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        migration: _SexMigration,
        stored: _StoredProject,
    ):
        """Nothing of it is kept, and the project is as it was."""
        # Arrange
        migration_service.start(stored.project.uid)
        migration._wrong_kind = True
        container = decoy.mock(cls=Container)
        decoy.when(container.get(MigrationService)).then_return(migration_service)

        # Act
        process_schema_migration.func.__wrapped__(  # type: ignore[attr-defined]
            stored.project.uid,
            ProjectStatus.COMPLETED.value,
            database_service=sqlite_database_service,
            container=container,
        )

        # Assert
        with sqlite_database_service.get_session() as session:
            project = session.get_one(DatabaseProject, stored.project.uid)
            assert project.status == ProjectStatus.COMPLETED
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
        migration_service.start(stored.project.uid)
        while_migrating = project_service.get_actions(stored.project.uid)

        # Assert
        assert before.migrate is True
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
        migration_service.start(stored.project.uid)

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
        migration_service.start(stored.project.uid)

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
        with pytest.raises(NotAllowedActionError, match="was exported"):
            migration_service.dry_run(stored.project.uid)
        with pytest.raises(NotAllowedActionError, match="was exported"):
            migration_service.start(stored.project.uid)

    def test_a_project_exported_while_waiting_to_be_migrated_is_not(
        self,
        sqlite_database_service: DatabaseService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """The task checks again."""
        # Arrange
        migration_service.start(stored.project.uid)
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, stored.project.uid)
            project.exported = datetime.datetime(2026, 1, 2)

        # Act & Assert
        with (
            pytest.raises(NotAllowedActionError, match="was exported"),
            sqlite_database_service.get_session() as session,
        ):
            migration_service.migrate(stored.project.uid, session=session)

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
            migration_service.dry_run(stored.project.uid)

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
            reason = schema_service.support_of(project).migrate_refusal()

        # Assert
        if migratable:
            assert reason is None
        else:
            assert reason is not None and "stored" in reason

    @pytest.mark.parametrize("source_is_root", [True])
    def test_a_remap_under_way_stops_when_the_project_is_migrated(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mapper_service: MapperService,
        migration_service: MigrationService,
        stored: _StoredProject,
    ):
        """It commits item by item, and asks again after each."""
        # Arrange
        remapped: list[UUID] = []

        def remap_and_start_a_migration(session, item, mappers) -> None:
            remapped.append(item.uid)
            if len(remapped) == 1:
                migration_service.start(stored.project.uid)

        monkeypatch.setattr(
            mapper_service, "_project_mappers_for_item", lambda item: [object()]
        )
        monkeypatch.setattr(
            mapper_service, "_remap_item_attributes", remap_and_start_a_migration
        )

        # Act & Assert
        with pytest.raises(ProjectNotEditableError, match="being migrated"):
            mapper_service.remap_item_hierarchy(stored.patient.uid)
        assert len(remapped) == 1


@pytest.mark.integration
class TestMovingMappers:
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
    def create_mapper_service(
        schema_service: SchemaService,
        sqlite_database_service: DatabaseService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
        migration: _SexMigration,
        mapper_injector: MapperInjectorInterface | None = None,
    ) -> MapperService:
        """The mapper service as the web app sets it up at startup."""
        mapper_service = MapperService(
            attribute_service,
            validation_service,
            schema_service,
            sqlite_database_service,
            review_service,
            mapper_injector,
        )
        mapper_service.set_up_mappers()
        return mapper_service

    def test_a_mapper_of_a_changed_attribute_is_moved(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
        migration: _SexMigration,
        original: UUID,
    ):
        # Act
        for _ in range(2):
            self.create_mapper_service(
                schema_service,
                sqlite_database_service,
                attribute_service,
                validation_service,
                review_service,
                migration,
            )

        # Assert
        self.assert_moved(sqlite_database_service, original)

    def test_a_mapper_is_moved_before_the_sheet_of_the_target_is_injected(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
        migration: _SexMigration,
        original: UUID,
    ):
        """A sheet of the target root names the mapper, which would otherwise
        be moved to it by its name, without its mapping items converted."""

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
        self.create_mapper_service(
            schema_service,
            sqlite_database_service,
            attribute_service,
            validation_service,
            review_service,
            migration,
            _TargetSheet(),
        )

        # Assert
        self.assert_moved(sqlite_database_service, original)

    def test_a_mapper_the_migration_fails_on_is_named(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
        migration: _SexMigration,
        original: UUID,
    ):
        # Arrange
        def broken(attribute: AnyAttribute) -> AnyAttribute | None:
            raise RuntimeError("broken")

        monkeypatch.setattr(migration, "migrate_attribute", broken)

        # Act & Assert
        with pytest.raises(ValueError, match="Mapper 'sex'"):
            self.create_mapper_service(
                schema_service,
                sqlite_database_service,
                attribute_service,
                validation_service,
                review_service,
                migration,
            )

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
    def test_nested_attributes_are_moved_and_the_mapping_kept(
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
        migrated = AttributeMigrator().migrate(attribute, moved_to)

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
            AttributeMigrator().migrate(attribute, schema.patient.attributes["sex"])

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
        cleared = AttributeMigrator.without_mapping_items(
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
