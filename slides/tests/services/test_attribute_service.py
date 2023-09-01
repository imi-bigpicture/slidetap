import pytest
from flask import Flask

from slides.database.attribute import CodeAttribute
from slides.database.schema.attribute_schema import CodeAttributeSchema
from slides.database.schema.schema import Schema
from slides.model.code import Code
from slides.services.attribute_service import AttributeService


@pytest.fixture
def attribute_service(app: Flask):
    yield AttributeService()


@pytest.mark.unittest
class TestAttributeService:
    def test_create_code_attribute(
        self, schema: Schema, attribute_service: AttributeService
    ):
        # Arrange
        collection_schema = CodeAttributeSchema.get_or_create(
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
        self, schema: Schema, attribute_service: AttributeService
    ):
        # Arrange
        collection_schema = CodeAttributeSchema.get_or_create(
            schema, "collection", "Collection method", "collection"
        )
        original_value = Code("code", "scheme", "meaning", "version")
        original_mappable_value = "mappable value"
        original_attribute = CodeAttribute(
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
        self, schema: Schema, attribute_service: AttributeService
    ):
        pass
