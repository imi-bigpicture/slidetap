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
import io
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from decoy import Decoy, matchers
from dishka import Container
from procrastinate import App as TaskApp
from slidetap_example import ExampleSchema
from sqlalchemy import select

from slidetap.database import (
    DatabaseImage,
    DatabaseSample,
)
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    ItemNamingFactoryInterface,
    MetadataExportInterface,
    MetadataImportInterface,
    PseudonymFactoryInterface,
)
from slidetap.image_processor.dicom_metadata import DicomMetadataWriter
from slidetap.model import (
    BatchCreate,
    BatchStatus,
    Dataset,
    EnumAttribute,
    File,
    ImageFormat,
    ImageStatus,
    Item,
    NotAllowedActionError,
    NotFoundError,
    Project,
    ProjectNotEditableError,
    ProjectStatus,
    ReviewLayout,
    ReviewStatus,
    ReviewUnitSchema,
    RootSchema,
    Sample,
)
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    DatasetService,
    ItemService,
    MapperService,
    MetadataSearchItemService,
    ProjectService,
    ReviewService,
    SchemaService,
    StorageService,
    TagService,
    ValidationService,
)
from slidetap.task import Scheduler, SlideTapTaskAppFactory
from slidetap.task.tasks import (
    download_and_pre_process_image,
    post_process_image,
    process_metadata_export,
    process_metadata_import,
    remap_batch_attributes,
    remap_dataset_attributes,
    store_batch_images_to_outbox,
)
from slidetap.web.services import (
    ImagePipelineService,
    MetadataExportService,
    MetadataImportService,
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
def other_is_root() -> bool:
    """Whether the second root is the root of new projects, whose projects can
    be changed, with the example root a previous root, or the other way
    round."""
    return True


@pytest.fixture()
def schema_service(
    schema: ExampleSchema,
    reviewed_other_schema: RootSchema,
    other_is_root: bool,
    schema_service_of: Callable[..., SchemaService],
) -> SchemaService:
    if other_is_root:
        return schema_service_of(reviewed_other_schema, schema)
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

    @pytest.mark.parametrize("other_is_root", [True, False])
    def test_each_project_is_validated_against_its_own_root(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        item_service: ItemService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
        other_is_root: bool,
    ):
        """The same value is valid in one root and not in the other, so a
        patient read against the wrong root is not valid. On either root, as
        the root of new projects."""
        # Arrange
        root = reviewed_other_schema if other_is_root else schema
        stored = self.store_project(sqlite_database_service, root)
        sex = root.samples[schema.patient_schema_uid].attributes["sex"].uid

        # Act
        valid = item_service.add(
            self.patient(stored, sex, "Male" if other_is_root else "M"), []
        )
        invalid = item_service.add(
            self.patient(stored, sex, "M" if other_is_root else "Male").model_copy(
                update={"identifier": "patient-2"}
            ),
            [],
        )

        # Assert
        assert valid.valid_attributes is True
        assert invalid.valid_attributes is False
        with sqlite_database_service.get_session() as session:
            item = sqlite_database_service.get_item(session, valid.uid)
            assert schema_service.root_of(item).uid == root.uid

    @pytest.mark.parametrize("other_is_root", [True, False])
    def test_each_project_is_reviewed_against_its_own_root(
        self,
        sqlite_database_service: DatabaseService,
        item_service: ItemService,
        review_service: ReviewService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
        other_is_root: bool,
    ):
        """Only the second root has a review unit, so only its patient is one
        to review."""
        # Arrange
        root = reviewed_other_schema if other_is_root else schema
        stored = self.store_project(sqlite_database_service, root)
        sex = root.samples[schema.patient_schema_uid].attributes["sex"].uid
        item_service.add(self.patient(stored, sex, "Unknown value"), [])

        # Act
        flagged = review_service.flag_invalid_review_units(stored.dataset.uid)

        # Assert
        assert flagged == (1 if other_is_root else 0)
        if other_is_root:
            assert [
                item.identifier
                for item in review_service.get_review_queue(
                    schema.patient_schema_uid, stored.dataset.uid
                )
            ] == ["patient-1"]

    def test_the_root_of_a_dataset_is_that_of_its_project(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
    ):
        """By its uid, in the session given or one of its own, or as it is."""
        # Arrange
        example = self.store_project(sqlite_database_service, schema)
        other = self.store_project(sqlite_database_service, reviewed_other_schema)

        # Act & Assert
        assert schema_service.root_of_dataset(example.dataset.uid).uid == schema.uid
        with sqlite_database_service.get_session() as session:
            dataset = sqlite_database_service.get_dataset(session, other.dataset.uid)
            assert (
                schema_service.root_of_dataset(other.dataset.uid, session).uid
                == reviewed_other_schema.uid
            )
            assert (
                schema_service.root_of_dataset(dataset, session).uid
                == reviewed_other_schema.uid
            )

    def test_a_dataset_without_a_project_has_no_root(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
    ):
        """Refused rather than put on a root it may not be on."""
        # Arrange
        dataset = Dataset(uid=uuid4(), name="dataset", schema_uid=schema.dataset.uid)
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_dataset(session, dataset)
            session.commit()

        # Act & Assert
        with pytest.raises(ValueError, match="has no project"):
            schema_service.root_of_dataset(dataset.uid)
        with sqlite_database_service.get_session() as session:
            database_dataset = sqlite_database_service.get_dataset(session, dataset.uid)
            with pytest.raises(ValueError, match="has no project"):
                schema_service.root_of(database_dataset, session)
            with pytest.raises(ValueError, match="has no project"):
                schema_service.support_of(database_dataset, session)

    @pytest.mark.parametrize("other_is_root", [False])
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

    def test_a_mapping_injected_again_is_applied_again(
        self,
        sqlite_database_service: DatabaseService,
        item_service: ItemService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
    ):
        """The sheet wins: what an attribute was mapped to is what the sheet
        now says."""
        # Arrange
        other = self.store_project(sqlite_database_service, reviewed_other_schema)
        other_sex = reviewed_other_schema.samples[schema.patient_schema_uid]
        other_sex = other_sex.attributes["sex"].uid
        mapper = mapper_service.get_or_create_mapper("sex", other_sex)
        mapper_service.get_or_create_mapping(
            mapper.uid,
            "^man$",
            EnumAttribute(uid=uuid4(), schema_uid=other_sex, original_value="Female"),
        )
        unmapped = self.patient(other, other_sex, "")
        unmapped.attributes["sex"].original_value = None
        unmapped.attributes["sex"].mappable_value = "man"
        added = item_service.add(unmapped, [mapper.uid])

        # Act
        mapper_service.get_or_create_mapping(
            mapper.uid,
            "^man$",
            EnumAttribute(uid=uuid4(), schema_uid=other_sex, original_value="Male"),
        )

        # Assert
        assert item_service.get(added.uid).attributes["sex"].value == "Male"

    @pytest.mark.parametrize("change", ["sheet", "deleted"])
    def test_an_exported_project_keeps_what_it_was_mapped_to(
        self,
        sqlite_database_service: DatabaseService,
        item_service: ItemService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
        change: str,
    ):
        """What went out stays as it went out, whether the sheet changes what
        the mapping maps to or the mapping is deleted."""
        # Arrange
        other = self.store_project(sqlite_database_service, reviewed_other_schema)
        other_sex = reviewed_other_schema.samples[schema.patient_schema_uid]
        other_sex = other_sex.attributes["sex"].uid
        mapper = mapper_service.get_or_create_mapper("sex", other_sex)
        mapping = mapper_service.get_or_create_mapping(
            mapper.uid,
            "^man$",
            EnumAttribute(uid=uuid4(), schema_uid=other_sex, original_value="Female"),
        )
        unmapped = self.patient(other, other_sex, "")
        unmapped.attributes["sex"].original_value = None
        unmapped.attributes["sex"].mappable_value = "man"
        added = item_service.add(unmapped, [mapper.uid])
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, other.project.uid)
            project.status = ProjectStatus.EXPORT_COMPLETE

        # Act
        if change == "sheet":
            mapper_service.get_or_create_mapping(
                mapper.uid,
                "^man$",
                EnumAttribute(uid=uuid4(), schema_uid=other_sex, original_value="Male"),
            )
        else:
            mapper_service.delete_mapping(mapping.uid)

        # Assert
        assert item_service.get(added.uid).attributes["sex"].value == "Female"


@pytest.mark.integration
class TestProjectList:
    def test_projects_of_every_root_are_listed(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
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
        example = TestProjectsOnTwoRoots.store_project(sqlite_database_service, schema)
        other = TestProjectsOnTwoRoots.store_project(
            sqlite_database_service, reviewed_other_schema
        )

        # Act
        projects = project_service.get_all()

        # Assert
        assert {project.uid for project in projects} == {
            example.project.uid,
            other.project.uid,
        }

    def test_a_project_is_created_on_the_root_of_new_projects(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        review_service: ReviewService,
        mapper_service: MapperService,
        reviewed_other_schema: RootSchema,
    ):
        """With its dataset, validated once it has its project, and its default
        batch, in one go."""
        # Arrange
        attribute_service = AttributeService(
            schema_service, validation_service, sqlite_database_service, review_service
        )
        batch_service = BatchService(
            schema_service, validation_service, sqlite_database_service, review_service
        )
        metadata_import_interface = decoy.mock(cls=MetadataImportInterface)
        dataset = Dataset(
            uid=uuid4(), name="new", schema_uid=reviewed_other_schema.dataset.uid
        )
        project = Project(
            uid=uuid4(),
            name="new",
            root_schema_uid=reviewed_other_schema.uid,
            schema_uid=reviewed_other_schema.project.uid,
            dataset_uid=dataset.uid,
            created=datetime.datetime(2026, 1, 1),
        )
        decoy.when(metadata_import_interface.create_dataset("new")).then_return(dataset)
        decoy.when(
            metadata_import_interface.create_project("new", dataset.uid)
        ).then_return(project)
        metadata_import_service = MetadataImportService(
            decoy.mock(cls=Scheduler),
            batch_service,
            DatasetService(
                attribute_service,
                schema_service,
                validation_service,
                mapper_service,
                sqlite_database_service,
            ),
            ProjectService(
                attribute_service=attribute_service,
                batch_service=batch_service,
                schema_service=schema_service,
                validation_service=validation_service,
                mapper_service=mapper_service,
                database_service=sqlite_database_service,
                storage_service=decoy.mock(cls=StorageService),
            ),
            sqlite_database_service,
            schema_service,
            decoy.mock(cls=MetadataSearchItemService),
            metadata_import_interface,
        )

        # Act
        created = metadata_import_service.create_project("new")

        # Assert
        assert created.uid == project.uid
        with sqlite_database_service.get_session() as session:
            stored = sqlite_database_service.get_project(session, project.uid)
            assert stored.root_schema_uid == reviewed_other_schema.uid
            assert stored.dataset.uid == dataset.uid
            assert stored.dataset.valid_attributes is not None
            default_batch = sqlite_database_service.get_batch(
                session, stored.default_batch_uid
            )
            assert default_batch.name == "Default"

    def test_projects_on_a_root_not_provided_refuse_the_start(
        self,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        """There would be no schema to read them with: the application does
        not start, and says which roots are missing and what to do."""
        # Arrange
        retired = schema.model_copy(update={"uid": uuid4(), "name": "Retired schema"})
        for _ in range(2):
            TestProjectsOnTwoRoots.store_project(sqlite_database_service, retired)

        # Act & Assert
        with pytest.raises(ValueError, match="not provided") as refused:
            schema_service_of(schema, reviewed_other_schema)
        assert f"{retired.uid} (2 projects)" in str(refused.value)
        assert "previous root" in str(refused.value)

    def test_projects_on_a_root_not_provided_refuse_the_start_of_a_worker(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        """As they do of the web app: the worker checks the roots when its
        task app is created."""
        # Arrange
        retired = schema.model_copy(update={"uid": uuid4(), "name": "Retired schema"})
        TestProjectsOnTwoRoots.store_project(sqlite_database_service, retired)
        container = decoy.mock(cls=Container)
        decoy.when(container.get(SchemaService)).then_do(
            lambda *_: schema_service_of(schema, reviewed_other_schema)
        )

        # Act & Assert
        with pytest.raises(ValueError, match="not provided"):
            SlideTapTaskAppFactory.create(container)
        decoy.verify(container.get(TaskApp), times=0)

    def test_what_is_stored_off_its_root_refuses_the_start(
        self,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        reviewed_other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        """A root changed without being given a new uid leaves items on
        schemas it no longer has: the application does not start, and says
        which roots and what to do."""
        # Arrange
        example = TestProjectsOnTwoRoots.store_project(sqlite_database_service, schema)
        other = TestProjectsOnTwoRoots.store_project(
            sqlite_database_service, reviewed_other_schema
        )
        with sqlite_database_service.get_session() as session:
            for stored, schema_uid in (
                (example, schema.patient_schema_uid),
                (example, uuid4()),
                (other, schema.patient_schema_uid),
            ):
                session.add(
                    DatabaseSample(
                        stored.dataset.uid, stored.batch_uid, schema_uid, "sample"
                    )
                )
            session.commit()

        # Act & Assert
        with pytest.raises(ValueError, match="does not have") as refused:
            schema_service_of(reviewed_other_schema, schema)
        assert f"({schema.uid}): 1 items and 0 attributes" in str(refused.value)
        assert str(reviewed_other_schema.uid) not in str(refused.value)
        assert "Give the changed root a new uid" in str(refused.value)


class _Pseudonyms(PseudonymFactoryInterface):
    """Mints a pseudonym for every item."""

    def create_pseudonym(self, item: Item) -> str | None:
        return f"PSEUDO-{uuid4().hex[:8]}"


class _Naming(ItemNamingFactoryInterface):
    """Names every item the same."""

    def create_identifier(self, item: Item) -> str:
        return "named"


@pytest.mark.integration
class TestViewOnlyRoot:
    """The second root is view only, and the example root editable. Every
    change to a project on the second root is refused, by the service and by
    the task, and nothing of the project is changed."""

    @pytest.fixture()
    def other_is_root(self) -> bool:
        return False

    @pytest.fixture()
    def example(
        self, sqlite_database_service: DatabaseService, schema: ExampleSchema
    ) -> StoredProject:
        return TestProjectsOnTwoRoots.store_project(sqlite_database_service, schema)

    @pytest.fixture()
    def other(
        self,
        sqlite_database_service: DatabaseService,
        reviewed_other_schema: RootSchema,
    ) -> StoredProject:
        return TestProjectsOnTwoRoots.store_project(
            sqlite_database_service, reviewed_other_schema
        )

    @pytest.fixture()
    def project_service(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
    ) -> ProjectService:
        return ProjectService(
            attribute_service=decoy.mock(cls=AttributeService),
            batch_service=decoy.mock(cls=BatchService),
            schema_service=schema_service,
            validation_service=validation_service,
            mapper_service=decoy.mock(cls=MapperService),
            database_service=sqlite_database_service,
            storage_service=decoy.mock(cls=StorageService),
        )

    def test_a_project_on_a_view_only_root_is_offered_no_change(
        self,
        project_service: ProjectService,
        example: StoredProject,
        other: StoredProject,
    ):
        # Act
        on_example = project_service.get_actions(example.project.uid)
        on_other = project_service.get_actions(other.project.uid)

        # Assert
        # Nothing migrates the projects on either root.
        migration = {"has_migration", "migrate_refusal"}
        assert set(on_example.model_dump(exclude=migration).values()) == {True}
        assert set(on_other.model_dump(exclude=migration).values()) == {False}
        assert on_other.edit is False

    def test_editing_is_refused(
        self,
        sqlite_database_service: DatabaseService,
        item_service: ItemService,
        review_service: ReviewService,
        mapper_service: MapperService,
        project_service: ProjectService,
        schema: ExampleSchema,
        other: StoredProject,
    ):
        """Adding an item, review decisions, remapping, and editing the project
        are some of what editing covers."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            session.add(
                DatabaseSample(
                    other.dataset.uid,
                    other.batch_uid,
                    schema.patient_schema_uid,
                    "patient-1",
                )
            )
            session.commit()
            stored = session.scalars(select(DatabaseSample)).one()
            stored_uid = stored.uid
        patient = TestProjectsOnTwoRoots.patient(
            other, schema.patient.attributes["sex"].uid, "M"
        )

        # Act & Assert
        with pytest.raises(ProjectNotEditableError):
            item_service.add(patient, [])
        with pytest.raises(ProjectNotEditableError):
            review_service.set_review_status(stored_uid, ReviewStatus.REVIEWED)
        with pytest.raises(ProjectNotEditableError):
            mapper_service.remap_item(stored_uid)
        with pytest.raises(ProjectNotEditableError):
            project_service.update(other.project)
        with pytest.raises(ProjectNotEditableError):
            item_service.clear_pseudonyms(other.dataset.uid)
        with sqlite_database_service.get_session() as session:
            assert len(session.scalars(select(DatabaseSample)).all()) == 1

    @pytest.mark.asyncio
    async def test_search_is_refused(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        other: StoredProject,
    ):
        # Arrange
        metadata_import_interface = decoy.mock(cls=MetadataImportInterface)
        metadata_import_service = MetadataImportService(
            decoy.mock(cls=Scheduler),
            decoy.mock(cls=BatchService),
            decoy.mock(cls=DatasetService),
            decoy.mock(cls=ProjectService),
            sqlite_database_service,
            schema_service,
            decoy.mock(cls=MetadataSearchItemService),
            metadata_import_interface,
        )
        file = File("search.json", "application/json", io.BytesIO(b"{}"))

        # Act & Assert
        with pytest.raises(ProjectNotEditableError):
            await metadata_import_service.search(other.batch_uid, file)
        decoy.verify(metadata_import_interface.parse_file(file), times=0)

    def test_the_search_task_is_refused(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        item_service: ItemService,
        other: StoredProject,
    ):
        """Queued before the root became view only, as across a deploy."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            batch = sqlite_database_service.get_batch(session, other.batch_uid)
            batch.status = BatchStatus.METADATA_SEARCHING
        metadata_import_interface = decoy.mock(cls=MetadataImportInterface)

        # Act
        process_metadata_import.func.__wrapped__(
            batch_uid=other.batch_uid,
            search_parameters={},
            metadata_import_interface=metadata_import_interface,
            database_service=sqlite_database_service,
            batch_service=self._batch_service(sqlite_database_service, schema_service),
            item_service=item_service,
            search_item_service=MetadataSearchItemService(sqlite_database_service),
            schema_service=schema_service,
        )

        # Assert
        decoy.verify(
            metadata_import_interface.search(
                matchers.Anything(), matchers.Anything(), matchers.Anything()
            ),
            times=0,
        )
        with sqlite_database_service.get_session() as session:
            batch = sqlite_database_service.get_batch(session, other.batch_uid)
            assert batch.status == BatchStatus.FAILED

    @pytest.mark.asyncio
    async def test_image_processing_is_refused(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        other: StoredProject,
    ):
        # Arrange
        batch_service = decoy.mock(cls=BatchService)
        image_pipeline_service = ImagePipelineService(
            decoy.mock(cls=Scheduler),
            batch_service,
            schema_service,
            sqlite_database_service,
        )

        # Act & Assert
        with pytest.raises(ProjectNotEditableError):
            await image_pipeline_service.pre_process_batch(other.batch_uid)
        with pytest.raises(ProjectNotEditableError):
            await image_pipeline_service.export(other.batch_uid)
        decoy.verify(
            batch_service.set_as_pre_processing(
                matchers.Anything(), matchers.Anything()
            ),
            times=0,
        )

    def test_the_image_tasks_are_refused(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        other: StoredProject,
    ):
        # Arrange
        image_uid = self._image(sqlite_database_service, schema, other)
        image_import_interface = decoy.mock(cls=ImageImportInterface)
        image_export_interface = decoy.mock(cls=ImageExportInterface)
        batch_service = decoy.mock(cls=BatchService)

        # Act
        download_and_pre_process_image.func.__wrapped__(
            image_uid=image_uid,
            task_id="task",
            image_import_interface=image_import_interface,
            metadata_import_interface=decoy.mock(cls=MetadataImportInterface),
            database_service=sqlite_database_service,
            review_service=decoy.mock(cls=ReviewService),
            batch_service=batch_service,
            attribute_service=decoy.mock(cls=AttributeService),
            schema_service=schema_service,
        )
        post_process_image.func.__wrapped__(
            image_uid=image_uid,
            task_id="task",
            image_export_interface=image_export_interface,
            database_service=sqlite_database_service,
            batch_service=batch_service,
            storage_service=decoy.mock(cls=StorageService),
            schema_service=schema_service,
        )

        # Assert
        decoy.verify(
            image_import_interface.download(matchers.Anything(), matchers.Anything()),
            times=0,
        )
        with sqlite_database_service.get_session() as session:
            image = session.get(DatabaseImage, image_uid)
            assert image is not None
            assert image.status == ImageStatus.NOT_STARTED
        # The batch is failed, rather than left waiting for what is not done.
        decoy.verify(
            batch_service.set_as_failed(
                matchers.Anything(),
                matchers.Anything(),
                message=matchers.StringMatching("view only"),
            ),
            times=2,
        )

    @pytest.mark.asyncio
    async def test_export_is_refused(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        other: StoredProject,
    ):
        # Arrange
        project_service = decoy.mock(cls=ProjectService)
        metadata_export_service = MetadataExportService(
            decoy.mock(cls=Scheduler),
            project_service,
            sqlite_database_service,
            schema_service,
            decoy.mock(cls=MetadataExportInterface),
        )
        image_pipeline_service = ImagePipelineService(
            decoy.mock(cls=Scheduler),
            decoy.mock(cls=BatchService),
            schema_service,
            sqlite_database_service,
        )

        # Act & Assert
        with pytest.raises(ProjectNotEditableError):
            await metadata_export_service.export(other.project)
        with pytest.raises(ProjectNotEditableError):
            await image_pipeline_service.store_project(other.project.uid)
        decoy.verify(project_service.set_as_exporting(other.project), times=0)

    def test_the_export_tasks_are_refused(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        other: StoredProject,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, other.project.uid)
            project.status = ProjectStatus.EXPORTING
            batch = sqlite_database_service.get_batch(session, other.batch_uid)
            batch.status = BatchStatus.IMAGE_STORING
        metadata_export_interface = decoy.mock(cls=MetadataExportInterface)
        image_export_interface = decoy.mock(cls=ImageExportInterface)
        batch_service = decoy.mock(cls=BatchService)
        project_service = ProjectService(
            attribute_service=decoy.mock(cls=AttributeService),
            batch_service=decoy.mock(cls=BatchService),
            schema_service=schema_service,
            validation_service=validation_service,
            mapper_service=decoy.mock(cls=MapperService),
            database_service=sqlite_database_service,
            storage_service=decoy.mock(cls=StorageService),
        )

        # Act
        process_metadata_export.func.__wrapped__(
            project_id=other.project.uid,
            metadata_export_interface=metadata_export_interface,
            project_service=project_service,
            database_service=sqlite_database_service,
            schema_service=schema_service,
        )
        store_batch_images_to_outbox.func.__wrapped__(
            batch_uid=other.batch_uid,
            database_service=sqlite_database_service,
            batch_service=batch_service,
            storage_service=decoy.mock(cls=StorageService),
            schema_service=schema_service,
            image_export_interface=image_export_interface,
            dicom_metadata_writer=DicomMetadataWriter(),
        )

        # Assert
        decoy.verify(
            metadata_export_interface.export(matchers.Anything(), matchers.Anything()),
            times=0,
        )
        with sqlite_database_service.get_session() as session:
            project = sqlite_database_service.get_project(session, other.project.uid)
            assert project.status == ProjectStatus.COMPLETED
            batch = sqlite_database_service.get_batch(session, other.batch_uid)
            assert batch.status == BatchStatus.IMAGE_STORING
        decoy.verify(
            batch_service.set_as_failed(
                matchers.Anything(),
                matchers.Anything(),
                message=matchers.StringMatching("view only"),
            ),
            times=1,
        )

    def test_there_is_no_preview(
        self,
        decoy: Decoy,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        schema: ExampleSchema,
        other: StoredProject,
    ):
        # Arrange
        image_uid = self._image(sqlite_database_service, schema, other)
        metadata_export_interface = decoy.mock(cls=MetadataExportInterface)
        metadata_export_service = MetadataExportService(
            decoy.mock(cls=Scheduler),
            decoy.mock(cls=ProjectService),
            sqlite_database_service,
            schema_service,
            metadata_export_interface,
        )

        # Act
        preview = metadata_export_service.preview_item(image_uid)

        # Assert
        assert preview is None
        decoy.verify(
            metadata_export_interface.preview_item(matchers.Anything()), times=0
        )

    def test_a_refused_remap_task_is_not_failed(self, decoy: Decoy):
        """A remap scheduled before the project became view only leaves it as
        it is, rather than fail and be retried."""
        # Arrange
        mapper_service = decoy.mock(cls=MapperService)
        batch_uid, dataset_uid = uuid4(), uuid4()
        decoy.when(mapper_service.remap_batch(batch_uid)).then_raise(
            NotAllowedActionError("The project is view only")
        )
        decoy.when(mapper_service.remap_dataset(dataset_uid)).then_raise(
            NotAllowedActionError("The project is view only")
        )

        # Act & Assert
        remap_batch_attributes.func.__wrapped__(
            batch_uid=batch_uid, mapper_service=mapper_service
        )
        remap_dataset_attributes.func.__wrapped__(
            dataset_uid=dataset_uid, mapper_service=mapper_service
        )

    def test_pseudonyms_and_naming_are_not_offered(
        self,
        sqlite_database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        review_service: ReviewService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        example: StoredProject,
        other: StoredProject,
    ):
        """An item is created with a pseudonym and named by the factories in
        a project on the editable root, and not created at all, nor the
        pseudonyms of the project changed, on the view-only root."""
        # Arrange
        attribute_service = AttributeService(
            schema_service, validation_service, sqlite_database_service, review_service
        )
        item_service = ItemService(
            attribute_service,
            TagService(sqlite_database_service),
            mapper_service,
            schema_service,
            validation_service,
            sqlite_database_service,
            review_service,
            pseudonym_factory=_Pseudonyms(),
            item_naming_factory=_Naming(),
        )

        # Act
        on_example = item_service.create(schema.patient_schema_uid, example.batch_uid)

        # Assert
        assert on_example is not None
        assert on_example.identifier == "named"
        assert on_example.pseudonym is not None
        with pytest.raises(ProjectNotEditableError):
            item_service.create(schema.patient_schema_uid, other.batch_uid)
        with pytest.raises(ProjectNotEditableError):
            item_service.repseudonymize(other.dataset.uid)
        with pytest.raises(ProjectNotEditableError):
            item_service.clear_pseudonyms(other.dataset.uid)
        with pytest.raises(ProjectNotEditableError):
            item_service.pseudonymize_identifiers(other.dataset.uid)

    @staticmethod
    def _image(
        database_service: DatabaseService, schema: ExampleSchema, stored: StoredProject
    ) -> UUID:
        with database_service.get_session() as session:
            image = DatabaseImage(
                stored.dataset.uid,
                stored.batch_uid,
                schema.image_schema_uid,
                "image-1",
                ImageFormat.OTHER_WSI,
            )
            session.add(image)
            session.commit()
            return image.uid

    @staticmethod
    def _batch_service(
        database_service: DatabaseService, schema_service: SchemaService
    ) -> BatchService:
        validation_service = ValidationService(schema_service, database_service)
        review_service = ReviewService(
            schema_service, validation_service, database_service
        )
        return BatchService(
            schema_service, validation_service, database_service, review_service
        )
