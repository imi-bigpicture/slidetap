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

import pytest
from slidetap.model import CodeAttributeSchema
from slidetap.model.attribute import CodeAttribute
from slidetap.model.code import Code
from slidetap.services import (
    AttributeService,
    DatabaseService,
    SchemaService,
    ValidationService,
)


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


@pytest.mark.unittest
class TestAttributeService:
    def test_get_code_attribute(
        self,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
        code_attribute_schema: CodeAttributeSchema,
    ):
        # Arrange
        attribute = attribute_service.create(code_attribute)

        # Act
        retrieved_attribute = attribute_service.get(attribute.uid)

        # Assert
        assert retrieved_attribute is not None
        assert retrieved_attribute.uid == code_attribute.uid
        assert retrieved_attribute.value == code_attribute.value
        assert retrieved_attribute.schema_uid == code_attribute_schema.uid

    def test_create_code_attribute(
        self,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
        code_attribute_schema: CodeAttributeSchema,
    ):
        # Arrange

        # Act
        attribute = attribute_service.create(code_attribute)

        # Assert
        assert attribute.value is not None
        assert attribute.value == code_attribute.value
        assert attribute.schema_uid == code_attribute_schema.uid

    def test_update_code_attribute(
        self,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
        code_attribute_schema: CodeAttributeSchema,
    ):
        # Arrange
        original_attribute = attribute_service.create(code_attribute)
        update_value = Code(
            code="code 2",
            scheme="scheme 2",
            meaning="meaning 2",
            scheme_version="version 2",
        )
        updated_attribute = code_attribute.model_copy(
            update={"updated_value": update_value},
        )

        # Act
        updated_attribute = attribute_service.update(updated_attribute)

        # Assert
        assert updated_attribute.value is not None
        assert updated_attribute.value == update_value
        assert updated_attribute.schema_uid == code_attribute_schema.uid
        assert updated_attribute.uid == original_attribute.uid

    # def test_create_object_attribute(
    #     self, schema: DatabaseRootSchema, attribute_service: AttributeService
    # ):
    #     # Arrange
    #     child_1_schema = DatabaseCodeAttributeSchema.get_or_create(
    #         schema, "child_1", "Child 1"
    #     )
    #     child_1_value = Code("code", "scheme", "meaning", "version")
    #     child_2_schema = DatabaseCodeAttributeSchema.get_or_create(
    #         schema, "child_2", "Child 2"
    #     )
    #     child_2_value = Code("code 2", "scheme 2", "meaning 2", "version 2")
    #     object_schema = DatabaseObjectAttributeSchema.get_or_create(
    #         schema, "object", "Object", [child_1_schema, child_2_schema]
    #     )
    #     attribute_data = {
    #         "tag": "object",
    #         "value": {
    #             "child_1": {
    #                 "tag": "child_1",
    #                 "value": child_1_value,
    #                 "schema_uid": child_1_schema.uid,
    #                 "mappable_value": "mappable value",
    #                 "display_name": "Child 1",
    #                 "attribute_value_type": child_1_schema.attribute_value_type,
    #             },
    #             "child_2": {
    #                 "tag": "child_2",
    #                 "value": child_2_value,
    #                 "schema_uid": child_2_schema.uid,
    #                 "mappable_value": "mappable value",
    #                 "display_name": "Child 2",
    #                 "attribute_value_type": child_2_schema.attribute_value_type,
    #             },
    #         },
    #         "schema_uid": object_schema.uid,
    #         "mappable_value": "mappable value",
    #         "display_name": "Object",
    #         "attribute_value_type": object_schema.attribute_value_type,
    #     }

    #     # Act
    #     attribute = attribute_service.create(object_schema, attribute_data)

    #     # Assert
    #     assert isinstance(attribute, DatabaseObjectAttribute)
    #     assert attribute.schema == object_schema
    #     assert attribute.value is not None
    #     child_1 = attribute.attributes["child_1"]
    #     assert child_1.value is not None
    #     assert child_1.value == child_1_value
    #     assert child_1.schema == child_1_schema
    #     child_2 = attribute.attributes["child_2"]
    #     assert child_2.value is not None
    #     assert child_2.value == child_2_value
    #     assert child_2.schema == child_2_schema
