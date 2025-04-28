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

from typing import Any, Dict, Mapping
from uuid import UUID

import pytest
from slidetap.model import (
    CodeAttribute,
    ObjectAttribute,
    Sample,
)
from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.code import Code
from slidetap.serialization import AttributeModel
from slidetap.serialization.item import SampleModel


@pytest.mark.unittest
class TestSerialization:
    def test_dump_code(self, code_attribute: CodeAttribute):
        # Arrange

        # Act
        dumped = AttributeModel().dump(code_attribute)

        # Assert
        assert isinstance(code_attribute.original_value, Code)
        assert isinstance(dumped, dict)
        assert dumped["mappableValue"] == code_attribute.mappable_value
        assert dumped["uid"] == str(code_attribute.uid)
        assert dumped["originalValue"]["code"] == code_attribute.original_value.code
        assert dumped["originalValue"]["scheme"] == code_attribute.original_value.scheme
        assert (
            dumped["originalValue"]["meaning"] == code_attribute.original_value.meaning
        )
        assert (
            dumped["originalValue"]["schemeVersion"]
            == code_attribute.original_value.scheme_version
        )
        assert dumped["schemaUid"] == str(code_attribute.schema_uid)
        assert dumped["attributeValueType"] == AttributeValueType.CODE.value

    def test_load_code(
        self,
        code_attribute: CodeAttribute,
        dumped_code_attribute: Dict[str, Any],
    ):
        # Arrange
        # Act
        loaded = AttributeModel().load(dumped_code_attribute)

        # Assert
        assert isinstance(code_attribute.value, Code)
        assert isinstance(loaded, CodeAttribute)
        assert isinstance(loaded.original_value, Code)
        assert loaded.mappable_value == code_attribute.mappable_value
        assert loaded.uid == code_attribute.uid
        assert loaded.original_value.code == code_attribute.value.code
        assert loaded.original_value.scheme == code_attribute.value.scheme
        assert loaded.original_value.meaning == code_attribute.value.meaning
        assert (
            loaded.original_value.scheme_version == code_attribute.value.scheme_version
        )
        assert loaded.schema_uid == code_attribute.schema_uid

    def test_dump_object_attribute(self, object_attribute: ObjectAttribute):
        # Arrange

        # Act
        dumped = AttributeModel().dump(object_attribute)

        # Assert
        assert isinstance(dumped, dict)

        assert dumped["mappableValue"] == object_attribute.mappable_value
        assert dumped["uid"] == str(object_attribute.uid)
        assert dumped["schemaUid"] == str(object_attribute.schema_uid)
        assert dumped["attributeValueType"] == AttributeValueType.OBJECT.value
        assert isinstance(dumped["originalValue"], dict)
        assert object_attribute.original_value is not None
        for (dumped_tag, dumped_value), (tag, value) in zip(
            dumped["originalValue"].items(), object_attribute.original_value.items()
        ):
            assert dumped_tag == tag
            assert isinstance(value, CodeAttribute)
            assert isinstance(value.original_value, Code)
            assert dumped_value["uid"] == str(value.uid)
            assert dumped_value["originalValue"]["code"] == value.original_value.code
            assert (
                dumped_value["originalValue"]["scheme"] == value.original_value.scheme
            )
            assert (
                dumped_value["originalValue"]["meaning"] == value.original_value.meaning
            )
            assert (
                dumped_value["originalValue"]["schemeVersion"]
                == value.original_value.scheme_version
            )
            assert dumped_value["schemaUid"] == str(value.schema_uid)
            assert dumped_value["attributeValueType"] == AttributeValueType.CODE.value

    def test_load_object_attribute(
        self,
        object_attribute: ObjectAttribute,
        dumped_object_attribute: Dict[str, Any],
    ):
        # Arrange

        # Act
        loaded = AttributeModel().load(dumped_object_attribute)

        # Assert
        assert isinstance(loaded, ObjectAttribute)
        assert loaded.mappable_value == object_attribute.mappable_value
        assert loaded.uid == object_attribute.uid
        assert loaded.schema_uid == object_attribute.schema_uid
        assert isinstance(loaded.original_value, Mapping)
        assert object_attribute.original_value is not None
        for (loaded_tag, loaded_value), (tag, value) in zip(
            loaded.original_value.items(), object_attribute.original_value.items()
        ):
            assert loaded_tag == tag
            assert isinstance(loaded_value, CodeAttribute)
            assert isinstance(value, CodeAttribute)
            assert isinstance(loaded_value.original_value, Code)
            assert isinstance(value.original_value, Code)
            assert loaded_value.uid == value.uid
            assert loaded_value.original_value.code == value.original_value.code
            assert loaded_value.original_value.scheme == value.original_value.scheme
            assert loaded_value.original_value.meaning == value.original_value.meaning
            assert (
                loaded_value.original_value.scheme_version
                == value.original_value.scheme_version
            )
            assert loaded_value.schema_uid == value.schema_uid

    def test_sample_dump(self, block: Sample):
        # Arrange
        model = SampleModel()

        # Act
        dumped = model.dump(block)

        # Assert
        assert isinstance(dumped, dict)
        assert dumped["uid"] == str(block.uid)
        assert dumped["selected"] == block.selected
        assert dumped["parents"] == [str(parent) for parent in block.parents]
        assert dumped["children"] == [str(child) for child in block.children]
        assert dumped["schemaUid"] == str(block.schema_uid)
        assert isinstance(dumped["attributes"], dict)
        for (dumped_tag, dumped_value), (tag, value) in zip(
            dumped["attributes"].items(), block.attributes.items()
        ):
            assert dumped_tag == tag
            assert isinstance(value, CodeAttribute)
            assert UUID(dumped_value["uid"]) == value.uid
            assert dumped_value["displayValue"] == value.display_value

    def test_sample_load(self, block: Sample, dumped_block: Dict[str, Any]):
        # Arrange
        model = SampleModel()

        # Act
        loaded = model.load(dumped_block)

        # Assert
        assert isinstance(loaded, Sample)
        assert loaded.uid == block.uid
        assert loaded.selected == block.selected
        assert loaded.parents == block.parents
        assert loaded.children == block.children
        assert isinstance(loaded.attributes, dict)
        for (loaded_tag, loaded_value), (tag, value) in zip(
            loaded.attributes.items(), block.attributes.items()
        ):
            assert isinstance(loaded_value.original_value, Code)
            assert loaded_tag == tag
            assert loaded_value.original_value == value.original_value
