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

from typing import Literal
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from slidetap.database import DatabaseAttribute
from slidetap.model import Code, CodeAttribute, CodeAttributeSchema
from slidetap.services import (
    AttributeService,
    DatabaseService,
    SchemaService,
    ValidationService,
)
from slidetap_example.schema import ExampleSchema
from sqlalchemy.orm import Session


@pytest.fixture()
def code_attribute_schema(schema: ExampleSchema):
    yield schema.specimen.attributes["collection"]


@pytest.fixture()
def code_attribute(code_attribute_schema: CodeAttributeSchema):
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=code_attribute_schema.uid,
        original_value=Code(code="code", scheme="scheme", meaning="meaning"),
    )


@pytest.fixture()
def schema_service(decoy: Decoy) -> SchemaService:
    return decoy.mock(cls=SchemaService)


@pytest.fixture()
def validation_service(decoy: Decoy) -> ValidationService:
    return decoy.mock(cls=ValidationService)


@pytest.fixture()
def database_service(decoy: Decoy) -> DatabaseService:
    return decoy.mock(cls=DatabaseService)


@pytest.fixture()
def attribute_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    database_service: DatabaseService,
):
    yield AttributeService(
        schema_service=schema_service,
        validation_service=validation_service,
        database_service=database_service,
    )


@pytest.fixture()
def parent_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def database_attribute(
    decoy: Decoy, parent: Literal["item", "project", "dataset"], parent_uid: UUID
) -> DatabaseAttribute:
    database_attribute = decoy.mock(cls=DatabaseAttribute)
    if parent == "item":
        decoy.when(database_attribute.attribute_item_uid).then_return(parent_uid)
        decoy.when(database_attribute.attribute_project_uid).then_return(None)
        decoy.when(database_attribute.attribute_dataset_uid).then_return(None)
    elif parent == "project":
        decoy.when(database_attribute.attribute_project_uid).then_return(parent_uid)
        decoy.when(database_attribute.attribute_item_uid).then_return(None)
        decoy.when(database_attribute.attribute_dataset_uid).then_return(None)
    elif parent == "dataset":
        decoy.when(database_attribute.attribute_dataset_uid).then_return(parent_uid)
        decoy.when(database_attribute.attribute_item_uid).then_return(None)
        decoy.when(database_attribute.attribute_project_uid).then_return(None)
    return database_attribute


@pytest.mark.unittest
class TestAttributeService:
    def test_get_code_attribute(
        self,
        decoy: Decoy,
        attribute_service: AttributeService,
        database_service: DatabaseService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        database_attribute = decoy.mock(cls=DatabaseAttribute)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(
            database_service.get_attribute(session, code_attribute.uid)
        ).then_return(database_attribute)
        decoy.when(database_attribute.model).then_return(code_attribute)

        # Act
        retrieved_attribute = attribute_service.get(code_attribute.uid)

        # Assert
        assert retrieved_attribute == code_attribute

    @pytest.mark.parametrize("parent", ["item", "project", "dataset"])
    def test_create_code_attribute(
        self,
        decoy: Decoy,
        attribute_service: AttributeService,
        database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        code_attribute: CodeAttribute,
        parent: Literal["item", "project", "dataset"],
        parent_uid: UUID,
        database_attribute: DatabaseAttribute,
    ):
        # Arrange
        session = decoy.mock(cls=Session)
        if parent == "item":
            decoy.when(database_attribute.attribute_item_uid).then_return(parent_uid)
            decoy.when(database_attribute.attribute_project_uid).then_return(None)
            decoy.when(database_attribute.attribute_dataset_uid).then_return(None)
        elif parent == "project":
            decoy.when(database_attribute.attribute_project_uid).then_return(parent_uid)
            decoy.when(database_attribute.attribute_item_uid).then_return(None)
            decoy.when(database_attribute.attribute_dataset_uid).then_return(None)
        elif parent == "dataset":
            decoy.when(database_attribute.attribute_dataset_uid).then_return(parent_uid)
            decoy.when(database_attribute.attribute_item_uid).then_return(None)
            decoy.when(database_attribute.attribute_project_uid).then_return(None)
        attribute_schema = decoy.mock(cls=CodeAttributeSchema)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(schema_service.get_attribute(code_attribute.schema_uid)).then_return(
            attribute_schema
        )
        decoy.when(
            database_service.add_attribute(session, code_attribute, attribute_schema)
        ).then_return(database_attribute)
        decoy.when(database_attribute.model).then_return(code_attribute)

        # Act
        attribute = attribute_service.create(code_attribute)

        # Assert
        assert attribute == code_attribute
        if parent == "item":
            decoy.verify(
                validation_service.validate_item_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )
        elif parent == "project":
            decoy.verify(
                validation_service.validate_project_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )
        elif parent == "dataset":
            decoy.verify(
                validation_service.validate_dataset_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )

    @pytest.mark.parametrize("parent", ["item", "project", "dataset"])
    def test_update_code_attribute(
        self,
        decoy: Decoy,
        attribute_service: AttributeService,
        database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        code_attribute: CodeAttribute,
        parent: Literal["item", "project", "dataset"],
        parent_uid: UUID,
        database_attribute: DatabaseAttribute,
    ):
        # Arrange
        update_value = Code(
            code="code 2",
            scheme="scheme 2",
            meaning="meaning 2",
            scheme_version="version 2",
        )
        updated_attribute = code_attribute.model_copy(
            update={"updated_value": update_value},
        )
        display_value = "display value"
        session = decoy.mock(cls=Session)
        attribute_schema = decoy.mock(cls=CodeAttributeSchema)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(
            schema_service.get_any_attribute(code_attribute.schema_uid)
        ).then_return(attribute_schema)
        decoy.when(attribute_schema.create_display_value(update_value)).then_return(
            display_value
        )
        decoy.when(
            database_service.get_attribute(session, updated_attribute.uid)
        ).then_return(database_attribute)
        decoy.when(database_attribute.model).then_return(updated_attribute)

        # Act
        result = attribute_service.update(updated_attribute)

        # Assert
        assert result == updated_attribute
        decoy.verify(database_attribute.set_value(update_value, display_value), times=1)
        decoy.verify(database_attribute.set_mappable_value(None), times=1)
        if parent == "item":
            decoy.verify(
                validation_service.validate_item_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )
        elif parent == "project":
            decoy.verify(
                validation_service.validate_project_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )
        elif parent == "dataset":
            decoy.verify(
                validation_service.validate_dataset_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )

    @pytest.mark.parametrize("parent", ["item", "project", "dataset"])
    def test_create_attribute(
        self,
        decoy: Decoy,
        attribute_service: AttributeService,
        database_service: DatabaseService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        parent: Literal["item", "project", "dataset"],
        parent_uid: UUID,
        database_attribute: DatabaseAttribute,
    ):
        # Arrange
        schema = CodeAttributeSchema(
            uid=uuid4(),
            tag="attribute",
            name="attribute",
            display_name="Attribute",
            optional=False,
            read_only=False,
            display_in_table=True,
        )
        value = Code(
            code="code", scheme="scheme", meaning="meaning", scheme_version="version"
        )
        attribute = CodeAttribute(
            uid=uuid4(),
            schema_uid=schema.uid,
            original_value=value,
            mappable_value="mappable value",
            display_value="Display Value",
        )
        session = decoy.mock(cls=Session)
        decoy.when(database_service.get_session()).then_enter_with(session)
        decoy.when(schema_service.get_attribute(attribute.schema_uid)).then_return(
            schema
        )
        decoy.when(
            database_service.add_attribute(session, attribute, schema)
        ).then_return(database_attribute)
        decoy.when(database_attribute.model).then_return(attribute)

        # Act
        result = attribute_service.create(attribute)

        # Assert
        assert result == attribute
        decoy.verify(
            validation_service.validate_attribute(database_attribute, session=session),
            times=1,
        )
        if parent == "item":
            decoy.verify(
                validation_service.validate_item_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )
        elif parent == "project":
            decoy.verify(
                validation_service.validate_project_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )
        elif parent == "dataset":
            decoy.verify(
                validation_service.validate_dataset_attributes(
                    parent_uid, session=session
                ),
                times=1,
            )
