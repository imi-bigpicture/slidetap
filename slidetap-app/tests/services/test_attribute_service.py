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
from flask import Flask
from slidetap.database.attribute import DatabaseCodeAttribute, DatabaseObjectAttribute
from slidetap.database.schema.attribute_schema import (
    DatabaseCodeAttributeSchema,
    DatabaseObjectAttributeSchema,
)
from slidetap.database.schema.root_schema import DatabaseRootSchema
from slidetap.model.code import Code
from slidetap.services.attribute_service import AttributeService


@pytest.fixture
def attribute_service(app: Flask):
    yield AttributeService()


@pytest.mark.unittest
class TestAttributeService:
    def test_get_code_attribute(
        self, schema: DatabaseRootSchema, attribute_service: AttributeService
    ):
        # Arrange
        code_schema = DatabaseCodeAttributeSchema.get_or_create(schema, "code", "Code")
        value = Code("code", "scheme", "meaning", "version")
        attribute = DatabaseCodeAttribute(code_schema, value, "mappable value")

        # Act
        retrieved_attribute = attribute_service.get(attribute.uid)

        # Assert
        assert retrieved_attribute is not None
        assert retrieved_attribute == attribute

    def test_create_code_attribute(
        self, schema: DatabaseRootSchema, attribute_service: AttributeService
    ):
        # Arrange
        collection_schema = DatabaseCodeAttributeSchema.get_or_create(
            schema, "collection", "Collection method", "collection"
        )
        value = Code("code", "scheme", "meaning", "version")
        attribute_data = {
            "tag": "collection",
            "value": value,
            "schema_uid": collection_schema.uid,
            "mappable_value": "mappable value",
            "display_name": "Collection method",
            "attribute_value_type": collection_schema.attribute_value_type,
        }

        # Act
        attribute = attribute_service.create(collection_schema, attribute_data)

        # Assert
        assert attribute.value is not None
        assert attribute.value == value
        assert attribute.schema == collection_schema

    def test_update_code_attribute(
        self, schema: DatabaseRootSchema, attribute_service: AttributeService
    ):
        # Arrange
        collection_schema = DatabaseCodeAttributeSchema.get_or_create(
            schema, "collection", "Collection method", "collection"
        )
        original_value = Code("code", "scheme", "meaning", "version")
        original_mappable_value = "mappable value"
        original_attribute = DatabaseCodeAttribute(
            collection_schema, original_value, original_mappable_value
        )
        update_value = Code("code 2", "scheme 2", "meaning 2", "version 2")
        update_mappable_value = "mappable value 2"
        update_data = {
            "tag": "collection",
            "value": update_value,
            "schema_uid": collection_schema.uid,
            "mappable_value": update_mappable_value,
            "display_name": "Collection method",
            "attribute_value_type": collection_schema.attribute_value_type,
        }

        # Act
        updated_attribute = attribute_service.update(original_attribute, update_data)

        # Assert
        assert updated_attribute.value is not None
        assert updated_attribute.value == update_value
        assert updated_attribute.mappable_value == update_mappable_value
        assert updated_attribute.schema == collection_schema
        assert updated_attribute.uid == original_attribute.uid

    def test_create_object_attribute(
        self, schema: DatabaseRootSchema, attribute_service: AttributeService
    ):
        # Arrange
        child_1_schema = DatabaseCodeAttributeSchema.get_or_create(
            schema, "child_1", "Child 1"
        )
        child_1_value = Code("code", "scheme", "meaning", "version")
        child_2_schema = DatabaseCodeAttributeSchema.get_or_create(
            schema, "child_2", "Child 2"
        )
        child_2_value = Code("code 2", "scheme 2", "meaning 2", "version 2")
        object_schema = DatabaseObjectAttributeSchema.get_or_create(
            schema, "object", "Object", [child_1_schema, child_2_schema]
        )
        attribute_data = {
            "tag": "object",
            "value": {
                "child_1": {
                    "tag": "child_1",
                    "value": child_1_value,
                    "schema_uid": child_1_schema.uid,
                    "mappable_value": "mappable value",
                    "display_name": "Child 1",
                    "attribute_value_type": child_1_schema.attribute_value_type,
                },
                "child_2": {
                    "tag": "child_2",
                    "value": child_2_value,
                    "schema_uid": child_2_schema.uid,
                    "mappable_value": "mappable value",
                    "display_name": "Child 2",
                    "attribute_value_type": child_2_schema.attribute_value_type,
                },
            },
            "schema_uid": object_schema.uid,
            "mappable_value": "mappable value",
            "display_name": "Object",
            "attribute_value_type": object_schema.attribute_value_type,
        }

        # Act
        attribute = attribute_service.create(object_schema, attribute_data)

        # Assert
        assert isinstance(attribute, DatabaseObjectAttribute)
        assert attribute.schema == object_schema
        assert attribute.value is not None
        child_1 = attribute.attributes["child_1"]
        assert child_1.value is not None
        assert child_1.value == child_1_value
        assert child_1.schema == child_1_schema
        child_2 = attribute.attributes["child_2"]
        assert child_2.value is not None
        assert child_2.value == child_2_value
        assert child_2.schema == child_2_schema
