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
from collections.abc import Callable
from uuid import uuid4

import pytest
from slidetap_example import ExampleSchema

from slidetap.external_interfaces import SchemaInterface
from slidetap.model import (
    AttributePath,
    CodeAttributeSchema,
    EnumAttributeSchema,
    ListAttributeSchema,
    NotFoundError,
    ObjectAttributeSchema,
    Project,
    ProjectNotEditableError,
    ProjectStatus,
    RootSchema,
    StringAttributeSchema,
)
from slidetap.services import DatabaseService, SchemaService


@pytest.mark.unittest
class TestSchemaServiceRoots:
    def test_a_single_root_is_the_root_of_new_projects(
        self, schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
    ):
        # Arrange
        schema_service = schema_service_of(schema)

        # Act
        roots = schema_service.roots

        # Assert
        assert list(roots) == [schema.uid]
        assert schema_service.default_root.schema == schema

    def test_two_roots_sharing_unchanged_attributes_are_accepted(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        submitter = schema.project.attributes["submitter"]

        # Act
        schema_service = schema_service_of(schema, other_schema)

        # Assert
        assert set(schema_service.roots) == {schema.uid, other_schema.uid}
        assert schema_service.default_root.schema == schema
        assert schema_service.get_attribute(submitter.uid) == submitter

    def test_the_same_attribute_uid_with_two_definitions_is_refused(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        patient = other_schema.samples[schema.patient_schema_uid]
        sex = patient.attributes["sex"]
        assert isinstance(sex, EnumAttributeSchema)
        conflicting = other_schema.model_copy(
            update={
                "samples": {
                    **other_schema.samples,
                    patient.uid: patient.model_copy(
                        update={
                            "attributes": {
                                "sex": sex.model_copy(
                                    update={"uid": schema.patient.attributes["sex"].uid}
                                )
                            }
                        }
                    ),
                }
            }
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Conflicting attribute schemas"):
            schema_service_of(schema, conflicting)

    def test_item_schemas_are_looked_up_within_the_root(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        schema_service = schema_service_of(schema, other_schema)

        # Act
        in_example = schema_service.get_root(schema.uid).get_item(
            schema.patient_schema_uid
        )
        in_other = schema_service.get_root(other_schema.uid).get_item(
            schema.patient_schema_uid
        )

        # Assert
        assert in_example.attributes["sex"].uid == schema.patient.attributes["sex"].uid
        assert in_other.attributes["sex"].uid != in_example.attributes["sex"].uid

    def test_attribute_schemas_are_looked_up_across_roots(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        schema_service = schema_service_of(schema, other_schema)
        other_sex = other_schema.samples[schema.patient_schema_uid].attributes["sex"]

        # Act
        attribute = schema_service.get_attribute(other_sex.uid)

        # Assert
        assert attribute == other_sex

    def test_attribute_by_name_is_looked_up_within_the_root(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        schema_service = schema_service_of(schema, other_schema)

        # Act
        default = schema_service.get_attribute_by_name("sex")
        other = schema_service.get_attribute_by_name("sex", other_schema.uid)

        # Assert
        assert default.uid == schema.patient.attributes["sex"].uid
        assert (
            other.uid
            == other_schema.samples[schema.patient_schema_uid].attributes["sex"].uid
        )

    def test_root_of_project(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        schema_service = schema_service_of(schema, other_schema)
        project = Project(
            uid=uuid4(),
            name="project",
            root_schema_uid=other_schema.uid,
            schema_uid=other_schema.project.uid,
            dataset_uid=uuid4(),
            created=datetime.datetime(2021, 1, 1),
        )

        # Act
        root = schema_service.root_of(project)

        # Assert
        assert root.uid == other_schema.uid

    def test_a_root_is_a_family_of_its_own_by_default(self, schema: ExampleSchema):
        # Act
        family_uid = schema.family_uid

        # Assert
        assert family_uid == schema.uid
        assert schema.version is None

    def test_two_versions_of_a_root_share_its_family(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        schema_service = schema_service_of(schema, other_schema)

        # Act
        other = schema_service.get_root(other_schema.uid)

        # Assert
        assert other.family_uid == schema_service.default_root.family_uid
        assert other.display_name == f"{schema.name} 2"
        assert schema_service.default_root.display_name == schema.name

    def test_a_root_provided_twice_is_refused(
        self, schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
    ):
        """Even named otherwise: a uid is one root."""
        # Arrange
        renamed = schema.model_copy(update={"name": "Renamed", "version": "1.1"})

        # Act & Assert
        with pytest.raises(ValueError, match="more than once"):
            schema_service_of(schema, renamed)

    def test_a_root_is_listed_by_its_summary(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        schema_service = schema_service_of(schema, other_schema)

        # Act
        summaries = [root.summary() for root in schema_service.roots.values()]

        # Assert
        assert [
            (summary.uid, summary.version, summary.new_projects)
            for summary in summaries
        ] == [(schema.uid, None, True), (other_schema.uid, "2", False)]

    def test_a_root_that_is_not_provided_is_not_found(
        self, schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
    ):
        # Arrange
        schema_service = schema_service_of(schema)

        # Act & Assert
        with pytest.raises(NotFoundError):
            schema_service.get_root(uuid4())

    def test_a_schema_interface_without_a_root_cannot_be_created(self):
        """It does not say which root new projects are created with."""
        with pytest.raises(TypeError, match="root"):
            SchemaInterface()  # type: ignore[abstract]

    def test_a_single_root_is_the_editable_root_of_new_projects(
        self, stored_database_service: DatabaseService
    ):
        # Arrange
        class SingleRoot(SchemaInterface):
            def root(self) -> RootSchema:
                return ExampleSchema()

        # Act
        schema_service = SchemaService(SingleRoot(), stored_database_service)

        # Assert
        assert list(schema_service.roots) == [ExampleSchema().uid]
        assert schema_service.default_root.schema == ExampleSchema()
        assert schema_service.default_root.is_default
        assert schema_service.can_change(
            Project(
                uid=uuid4(),
                name="project",
                root_schema_uid=ExampleSchema().uid,
                schema_uid=ExampleSchema().project.uid,
                dataset_uid=uuid4(),
                created=datetime.datetime(2026, 1, 1),
            )
        )


@pytest.mark.unittest
class TestEditableRoots:
    def test_a_previous_root_is_view_only(
        self,
        schema: ExampleSchema,
        other_schema: RootSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        """Only the projects on the root of new projects can be changed."""
        # Arrange
        schema_service = schema_service_of(schema, other_schema)
        other = Project(
            uid=uuid4(),
            name="project",
            root_schema_uid=other_schema.uid,
            schema_uid=other_schema.project.uid,
            dataset_uid=uuid4(),
            created=datetime.datetime(2026, 1, 1),
        )

        # Act
        refusal = schema_service.change_refusal(other)

        # Assert
        assert not schema_service.get_root(other_schema.uid).is_default
        assert refusal == (
            f"{schema_service.get_root(other_schema.uid).display_name} is view only"
        )
        assert not schema_service.can_change(other)
        with pytest.raises(ProjectNotEditableError, match="view only"):
            schema_service.assert_can_change(other)

    def test_a_deleted_project_can_do_nothing(
        self, schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
    ):
        """Refused, whatever its root can do."""
        # Arrange
        schema_service = schema_service_of(schema)
        project = Project(
            uid=uuid4(),
            name="project",
            status=ProjectStatus.DELETED,
            root_schema_uid=schema.uid,
            schema_uid=schema.project.uid,
            dataset_uid=uuid4(),
            created=datetime.datetime(2026, 1, 1),
        )

        # Act & Assert
        assert schema_service.change_refusal(project) == "the project is deleted"
        assert not schema_service.can_change(project)
        with pytest.raises(ProjectNotEditableError, match="deleted"):
            schema_service.assert_can_change(project)


@pytest.fixture()
def diagnose_schema() -> CodeAttributeSchema:
    return CodeAttributeSchema(
        uid=uuid4(),
        tag="diagnose",
        name="diagnose",
        display_name="Diagnose",
        optional=False,
        read_only=False,
    )


def diagnose_list_schema(tag: str, entry: CodeAttributeSchema) -> ListAttributeSchema:
    return ListAttributeSchema(
        uid=uuid4(),
        tag=tag,
        name=tag,
        display_name=tag.capitalize(),
        optional=True,
        read_only=False,
        display_attributes_in_parent=False,
        attribute=entry,
    )


@pytest.fixture()
def statement_schema(diagnose_schema: CodeAttributeSchema) -> ObjectAttributeSchema:
    """A statement with two lists of the same diagnoses, which mean different
    things, and a note."""
    return ObjectAttributeSchema(
        uid=uuid4(),
        tag="statement",
        name="statement",
        display_name="Statement",
        optional=True,
        read_only=False,
        display_attributes_in_parent=False,
        display_value_tags=["diagnoses"],
        attributes={
            "diagnoses": diagnose_list_schema("diagnoses", diagnose_schema),
            "differentials": diagnose_list_schema("differentials", diagnose_schema),
            "note": StringAttributeSchema(
                uid=uuid4(),
                tag="note",
                name="note",
                display_name="Note",
                optional=True,
                read_only=False,
            ),
        },
    )


@pytest.fixture()
def statement_schema_service(
    schema: ExampleSchema,
    statement_schema: ObjectAttributeSchema,
    schema_service_of: Callable[..., SchemaService],
) -> SchemaService:
    """A schema service of the example root with the statement on its
    specimens."""
    specimen = schema.specimen
    root = schema.model_copy(
        update={
            "samples": {
                **schema.samples,
                specimen.uid: specimen.model_copy(
                    update={
                        "attributes": {
                            **specimen.attributes,
                            "statement": statement_schema,
                        }
                    }
                ),
            }
        }
    )
    return schema_service_of(root)


def attribute_path(*steps: str | int) -> AttributePath:
    return AttributePath(steps=steps)


@pytest.mark.unittest
class TestPathsHoldSameKind:
    def test_paths_to_two_entries_of_the_same_list_hold_the_same_kind(
        self,
        statement_schema_service: SchemaService,
        statement_schema: ObjectAttributeSchema,
    ):
        # Act & Assert
        statement_schema_service.assert_paths_hold_same_kind(
            statement_schema.uid,
            attribute_path("diagnoses", 0),
            statement_schema.uid,
            attribute_path("diagnoses", 3),
        )

    def test_paths_to_entries_of_lists_meaning_different_things_do_not(
        self,
        statement_schema_service: SchemaService,
        statement_schema: ObjectAttributeSchema,
    ):
        """The same diagnose schema, held by another list."""
        # Act & Assert
        with pytest.raises(ValueError):
            statement_schema_service.assert_paths_hold_same_kind(
                statement_schema.uid,
                attribute_path("diagnoses", 0),
                statement_schema.uid,
                attribute_path("differentials", 0),
            )

    def test_paths_to_different_schemas_are_not(
        self,
        statement_schema_service: SchemaService,
        statement_schema: ObjectAttributeSchema,
    ):
        # Act & Assert
        with pytest.raises(ValueError):
            statement_schema_service.assert_paths_hold_same_kind(
                statement_schema.uid,
                attribute_path("note"),
                statement_schema.uid,
                attribute_path("diagnoses", 0),
            )

    def test_a_path_with_no_steps_is_refused(
        self,
        statement_schema_service: SchemaService,
        statement_schema: ObjectAttributeSchema,
    ):
        # Act & Assert
        with pytest.raises(ValueError):
            statement_schema_service.assert_paths_hold_same_kind(
                statement_schema.uid,
                attribute_path(),
                statement_schema.uid,
                attribute_path("diagnoses", 0),
            )
