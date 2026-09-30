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
    EnumAttributeSchema,
    NotFoundError,
    Project,
    RootSchema,
)
from slidetap.services import SchemaService


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

    def test_a_root_provided_twice_is_refused(
        self, schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
    ):
        with pytest.raises(ValueError, match="more than once"):
            schema_service_of(schema, schema)
