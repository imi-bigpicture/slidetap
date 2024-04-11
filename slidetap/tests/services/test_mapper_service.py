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

from slidetap.database.attribute import CodeAttribute
from slidetap.database.mapper import Mapper, MappingItem
from slidetap.database.schema.attribute_schema import CodeAttributeSchema
from slidetap.database.schema.schema import Schema
from slidetap.model.code import Code
from slidetap.model.mapping_status import ValueStatus
from slidetap.services.mapper_service import MapperService


@pytest.fixture
def mapper_service(app: Flask):
    yield MapperService()


@pytest.fixture
def mapper(mapper_service: MapperService, schema: Schema):
    attribute_schema = CodeAttributeSchema.get(schema, "collection")
    yield mapper_service.create_mapper("new mapper", attribute_schema.uid)


@pytest.fixture
def mapping_attribute(schema: Schema):
    attribute_schema = CodeAttributeSchema.get(schema, "collection")
    yield CodeAttribute(attribute_schema, Code("code", "scheme", "meaning"))


@pytest.mark.unittest
class TestMapperService:
    def test_create_new_mapper(self, schema: Schema, mapper_service: MapperService):
        # Arrange
        attribute_schema = CodeAttributeSchema.get(schema, "collection")
        mapper_name = "new mapper"

        # Act
        mapper = mapper_service.create_mapper("new mapper", attribute_schema.uid)

        # Assert
        assert mapper.name == mapper_name
        assert mapper.attribute_schema == attribute_schema

    def test_create_throws_on_same_name_as_existing(
        self, schema: Schema, mapper_service: MapperService
    ):
        # Arrange
        existing_mapper_name = "existing mapper"
        attribute_schema_1 = CodeAttributeSchema.get(schema, "collection")
        attribute_schema_2 = CodeAttributeSchema.get(schema, "embedding")
        mapper_service.create_mapper(existing_mapper_name, attribute_schema_1.uid)

        # Act & Assert
        with pytest.raises(Exception):
            mapper_service.create_mapper(existing_mapper_name, attribute_schema_2.uid)

    def test_create_throws_on_same_attribute_schema_as_existing(
        self, schema: Schema, mapper_service: MapperService
    ):
        # Arrange
        existing_mapper_name = "existing mapper"
        new_mapper_name = "new mapper"
        attribute_schema = CodeAttributeSchema.get(schema, "collection")
        mapper_service.create_mapper(existing_mapper_name, attribute_schema.uid)

        # Act & Assert
        with pytest.raises(Exception):
            mapper_service.create_mapper(new_mapper_name, attribute_schema.uid)

    def test_update_mapper(self, mapper_service: MapperService, mapper: Mapper):
        # Arrange
        updated_name = "updated name"

        # Act
        updated_mapper = mapper_service.update_mapper(mapper.uid, updated_name)

        # Assert
        assert updated_mapper.name == updated_name

    def test_delete_mapper(self, mapper_service: MapperService, mapper: Mapper):
        # Arrange

        # Act
        mapper.delete()

        # Assert
        with pytest.raises(Exception):
            mapper_service.get_mapper(mapper.uid)

    def test_create_mapping(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"

        # Act
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )

        # Assert
        assert mapping.expression == expression
        assert mapping.attribute == mapping_attribute
        assert mapping in mapper.mappings
        assert mapping in mapping_attribute.parent_mappings
        assert mapping_attribute.mapping_item_uid is None

    def test_delete_mapping(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )

        # Act
        mapper_service.delete_mapping(mapping.uid)

        # Assert
        assert mapping not in mapper.mappings
        with pytest.raises(Exception):
            MappingItem.get_by_uid(mapping.uid)

    def test_create_mappable_attribute_no_mapping(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )
        assert isinstance(mapper.attribute_schema, CodeAttributeSchema)

        # Act
        attribute = CodeAttribute(mapper.attribute_schema, None, expression)

        # Assert
        assert attribute.mapping_status == ValueStatus.NOT_MAPPED
        assert attribute.mapping is None
        assert attribute.value is None

    def test_map_mappable_attribute(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )
        assert isinstance(mapper.attribute_schema, CodeAttributeSchema)
        attribute = CodeAttribute(mapper.attribute_schema, None, expression)

        # Act
        used_mapping_item = mapper_service.map(attribute)

        # Assert
        assert attribute.mapping_status == ValueStatus.MAPPED
        assert attribute.mapping == used_mapping_item
        assert attribute.value == mapping_attribute.value
        assert used_mapping_item == mapping

    def test_update_mapping_attribute(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )
        assert isinstance(mapper.attribute_schema, CodeAttributeSchema)
        attribute = CodeAttribute(mapper.attribute_schema, None, expression)
        mapper_service.map(attribute)
        updated_mapping_attribute = CodeAttribute(
            mapper.attribute_schema,
            Code("updated code", "updated schema", "updated meaning"),
        )

        # Act
        mapper_service.update_mapping(
            mapping.uid, expression, updated_mapping_attribute
        )

        # Assert
        assert attribute.mapping_status == ValueStatus.MAPPED
        assert attribute.value == updated_mapping_attribute.value
        assert attribute.mapping_item_uid == mapping.uid
        assert mapping.expression == expression
        assert mapping.attribute == updated_mapping_attribute

    def test_update_mapping_expression_no_longer_match(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        updated_expression = "other thing"
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )
        assert isinstance(mapper.attribute_schema, CodeAttributeSchema)
        attribute = CodeAttribute(mapper.attribute_schema, None, expression)
        mapper_service.map(attribute)

        # Act
        mapper_service.update_mapping(
            mapping.uid, updated_expression, mapping_attribute
        )

        # Assert
        assert mapping.expression == updated_expression
        assert mapping.attribute == mapping_attribute
        assert attribute.value is None
        assert attribute.mapping_item_uid is None

    def test_update_mapping_expression_now_matches(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        updated_expression = "other thing"
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )
        assert isinstance(mapper.attribute_schema, CodeAttributeSchema)
        attribute = CodeAttribute(mapper.attribute_schema, None, updated_expression)

        # Act
        mapper_service.update_mapping(
            mapping.uid, updated_expression, mapping_attribute
        )

        # Assert
        assert mapping.expression == updated_expression
        assert mapping.attribute == mapping_attribute
        assert attribute.value == mapping_attribute.value
        assert attribute.mapping_item_uid == mapping.uid

    def test_get_mapping(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        created_mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )

        # Act
        mapping = mapper_service.get_mapping(created_mapping.uid)

        # Assert
        assert mapping == created_mapping

    def test_get_mappings(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        created_mapping_1 = mapper_service.create_mapping(
            mapper.uid, "expression_1", mapping_attribute
        )
        created_mapping_2 = mapper_service.create_mapping(
            mapper.uid, "expression_2", mapping_attribute
        )

        # Act
        mappings = mapper_service.get_mappings(mapper.uid)

        # Assert
        assert len(mappings) == 2
        assert created_mapping_1 in mappings
        assert created_mapping_2 in mappings

    def test_map_matches_attribute_mappable_value(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )
        assert isinstance(mapper.attribute_schema, CodeAttributeSchema)
        attribute = CodeAttribute(mapper.attribute_schema, None, expression)

        # Act
        matched_mapping = mapper_service.map(attribute)

        # Assert
        assert matched_mapping == mapping
        assert attribute.value == mapping_attribute.value
        assert attribute.mapping_item_uid == mapping.uid

    def test_map_does_not_match_attribute_mappable_value(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        mappable_value = "something else"
        mapper_service.create_mapping(mapper.uid, expression, mapping_attribute)
        assert isinstance(mapper.attribute_schema, CodeAttributeSchema)
        attribute = CodeAttribute(mapper.attribute_schema, None, mappable_value)

        # Act
        matched_mapping = mapper_service.map(attribute)

        # Assert
        assert matched_mapping is None
        assert attribute.value is None
        assert attribute.mapping_item_uid is None

    def test_map_other_attribute_schema(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
        schema: Schema,
    ):
        # Arrange
        expression = "expression"
        mapper_service.create_mapping(mapper.uid, expression, mapping_attribute)
        attribute_schema = CodeAttributeSchema.get(schema, "embedding")
        attribute = CodeAttribute(attribute_schema, None, expression)

        # Act
        matched_mapping = mapper_service.map(attribute)

        # Assert
        assert matched_mapping is None
        assert attribute.value is None
        assert attribute.mapping_item_uid is None

    def test_get_mapping_for_attribute(
        self,
        mapper_service: MapperService,
        mapper: Mapper,
        mapping_attribute: CodeAttribute,
    ):
        # Arrange
        expression = "expression"
        mapping = mapper_service.create_mapping(
            mapper.uid, expression, mapping_attribute
        )
        assert isinstance(mapper.attribute_schema, CodeAttributeSchema)
        attribute = CodeAttribute(mapper.attribute_schema, None, expression)

        # Act
        matched_mapping = mapper_service.get_mapping_for_attribute(attribute)

        # Assert
        assert matched_mapping == mapping
        assert attribute.value is None
        assert attribute.mapping_item_uid is None
