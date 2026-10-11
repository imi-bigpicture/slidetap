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
from collections.abc import Callable, Collection, Mapping
from enum import Enum
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from slidetap_example import ExampleSchema
from sqlalchemy import create_engine

from slidetap.config import DatabaseConfig
from slidetap.database import Base
from slidetap.external_interfaces import (
    SchemaInterface,
    SchemaMigration,
)
from slidetap.external_interfaces.implementations.migration import (
    AttributeMigrator,
    EnumAttributeMigrator,
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnyAttribute,
    AnyEntitySchema,
    AttributeSchema,
    Batch,
    BatchStatus,
    Code,
    CodeAttribute,
    Dataset,
    EntityMigrationResult,
    Item,
    ItemSchema,
    Project,
    RootSchema,
    RootSchemaIndex,
    UnresolvedAttributeMigration,
)
from slidetap.services import DatabaseService, SchemaService


class ExampleSex(Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class OtherSex(Enum):
    MALE = "Male"
    FEMALE = "Female"


class SexMigration(SchemaMigration):
    """Moves projects from the example root to a second root of its family, as
    `other_schema` gives it, migrating the sex of the patient with an enum
    migrator, which leaves a sex with no counterpart unresolved, and moving
    every other attribute as it is.

    It migrates the project, the dataset, and the items of every item schema,
    or of the item schemas it is given, with the patient among them.
    """

    def __init__(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        item_schemas: Collection[UUID] | None = None,
    ):
        patient_uid = schema.patient_schema_uid
        self._sex = schema.patient.attributes["sex"]
        self._other_sex = other_schema.samples[patient_uid].attributes["sex"]
        self._sex_migrator = EnumAttributeMigrator(ExampleSex, OtherSex)
        self._unchanged = UnchangedAttributeMigrator()
        self._other_schema = other_schema
        self._other_root = RootSchemaIndex(other_schema, is_default=False)
        other_items = {
            **other_schema.samples,
            **other_schema.images,
            **other_schema.observations,
        }
        self._item_schemas: dict[UUID, ItemSchema] = {
            uid: other_items[uid]
            for uid in {**schema.samples, **schema.images, **schema.observations}
            if uid == patient_uid or item_schemas is None or uid in item_schemas
        }

    @property
    def migrated_item_schemas(self) -> Collection[UUID]:
        return self._item_schemas.keys()

    def migrate_project(self, project: Project) -> EntityMigrationResult | None:
        return self._move(project, self._other_schema.project)

    def migrate_dataset(self, dataset: Dataset) -> EntityMigrationResult | None:
        return self._move(dataset, self._other_schema.dataset)

    def migrate_item(self, item: Item) -> EntityMigrationResult | None:
        return self._move(item, self._item_schema(item.schema_uid))

    def migrate_item_schema(self, schema: ItemSchema) -> ItemSchema:
        return self._item_schema(schema.uid)

    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        target = self._attribute_schema(attribute.schema_uid)
        if target is None:
            return None
        return self._migrator(attribute).migrate(attribute, target).attribute

    def migrate_attribute_schema(
        self, schema: AttributeSchema
    ) -> AttributeSchema | None:
        return self._attribute_schema(schema.uid)

    def _move(
        self, entity: Project | Dataset | Item, target: AnyEntitySchema
    ) -> EntityMigrationResult:
        """Move the attributes of an entity to the target schema, the sex by
        its migrator."""
        return EntityMigrationResult(
            schema_uid=target.uid,
            attributes=self._move_attributes(entity.attributes, target.attributes),
            private_attributes=self._move_attributes(
                entity.private_attributes, target.private_attributes
            ),
        )

    def _move_attributes(
        self,
        attributes: Mapping[str, AnyAttribute],
        targets: Mapping[str, AttributeSchema],
    ) -> dict[str, AnyAttribute | UnresolvedAttributeMigration]:
        """Move attributes to the target attributes of their tags, unresolved
        where a value in effect is lost."""
        moved: dict[str, AnyAttribute | UnresolvedAttributeMigration] = {}
        for tag, attribute in attributes.items():
            target = targets.get(tag)
            if target is None:
                raise ValueError(
                    f"Attribute {attribute.uid} is held as {tag!r}, which the "
                    "target schema does not have."
                )
            migrated = self._migrator(attribute).migrate(attribute, target)
            moved[tag] = (
                UnresolvedAttributeMigration(
                    original=attribute,
                    proposed=migrated.attribute,
                    problem=" ".join(migrated.lost),
                )
                if migrated.lost
                else migrated.attribute
            )
        return moved

    def _migrator(self, attribute: AnyAttribute) -> AttributeMigrator:
        """Get the migrator of an attribute: of the sex, or moving it as it is."""
        if attribute.schema_uid == self._sex.uid:
            return self._sex_migrator
        return self._unchanged

    def _item_schema(self, schema_uid: UUID) -> ItemSchema:
        """Get the target of a migrated item schema."""
        target = self._item_schemas.get(schema_uid)
        if target is None:
            raise ValueError(f"Item schema {schema_uid} is not migrated.")
        return target

    def _attribute_schema(self, schema_uid: UUID) -> AttributeSchema | None:
        """Get the target of an attribute schema: of the sex, or the same
        schema where the second root has it."""
        if schema_uid == self._sex.uid:
            return self._other_sex
        return self._other_root.attributes.get(
            schema_uid
        ) or self._other_root.private_attributes.get(schema_uid)


@pytest.fixture
def schema():
    yield ExampleSchema()


@pytest.fixture
def schema_service_of(
    decoy: Decoy, sqlite_database_service: DatabaseService
) -> Callable[..., SchemaService]:
    """Builds a schema service as the plugin's interfaces provide it: of the
    root of new projects, the previous roots, and the migrations."""

    def schema_service_of(
        root: RootSchema,
        *previous_roots: RootSchema,
        migrations: Mapping[UUID, SchemaMigration] | None = None,
    ) -> SchemaService:
        schema_interface = decoy.mock(cls=SchemaInterface)
        decoy.when(schema_interface.root()).then_return(root)
        decoy.when(schema_interface.previous_roots()).then_return(previous_roots)
        for previous_root in previous_roots:
            migration = (migrations or {}).get(previous_root.uid)
            if migration is not None:
                decoy.when(schema_interface.migration_from(previous_root)).then_return(
                    migration
                )
        return SchemaService(schema_interface, sqlite_database_service)

    return schema_service_of


OTHER_ROOT_SCHEMA_UID = UUID("0d5b3c1e-9a0f-4f5e-8f55-2f7b5f0a6c11")
OTHER_SEX_SCHEMA_UID = UUID("5a0e2b67-3c1d-4e8a-9f0b-7d6c5e4f3a21")


@pytest.fixture
def other_schema(schema: ExampleSchema) -> RootSchema:
    """The example schema as a second root, a new version of it in its family.

    The same item schemas and relations under the same uids, with the sex of
    the patient changed: another uid and other allowed values. Every other
    attribute is shared with the example schema.
    """
    patient = schema.patient
    sex = patient.attributes["sex"].model_copy(
        update={"uid": OTHER_SEX_SCHEMA_UID, "allowed_values": ("Male", "Female")}
    )
    return RootSchema(
        uid=OTHER_ROOT_SCHEMA_UID,
        name=schema.name,
        version="2",
        family_uid=schema.family_uid,
        project=schema.project,
        dataset=schema.dataset,
        images=dict(schema.images),
        samples={
            **schema.samples,
            patient.uid: patient.model_copy(update={"attributes": {"sex": sex}}),
        },
        observations=dict(schema.observations),
    )


@pytest.fixture()
def sqlite_database_service(tmp_path: Path) -> DatabaseService:
    """A DatabaseService backed by a throwaway SQLite file.

    Named apart from the `database_service` fixtures in the service tests,
    which are Decoy mocks: a test that asks for this one gets a real database.
    """
    uri = f"sqlite:///{tmp_path / 'test.db'}"
    Base.metadata.create_all(bind=create_engine(uri))
    return DatabaseService(DatabaseConfig(uri, False))


@pytest.fixture()
def mapper_uid(sqlite_database_service: DatabaseService) -> UUID:
    with sqlite_database_service.get_session() as session:
        mapper = sqlite_database_service.add_mapper(
            session, "test-mapper", uuid4(), uuid4()
        )
        return mapper.uid


@pytest.fixture()
def code_attribute() -> CodeAttribute:
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=uuid4(),
        original_value=Code(code="code", scheme="scheme", meaning="meaning"),
    )


@pytest.fixture()
def dataset(schema: RootSchema):
    yield Dataset(
        uid=uuid4(),
        name="dataset name",
        schema_uid=schema.dataset.uid,
    )


@pytest.fixture()
def project(schema: RootSchema, dataset: Dataset):
    project = Project(
        uid=uuid4(),
        name="project name",
        root_schema_uid=schema.uid,
        schema_uid=schema.project.uid,
        dataset_uid=dataset.uid,
        created=datetime.datetime(2021, 1, 1),
        attributes={},
        mapper_groups=[],
    )
    yield project


@pytest.fixture()
def batch(project: Project):
    return Batch(
        uid=uuid4(),
        name="batch name",
        status=BatchStatus.INITIALIZED,
        project_uid=project.uid,
        is_default=True,
        created=datetime.datetime(2021, 1, 1),
    )
