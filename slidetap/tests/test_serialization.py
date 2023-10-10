from typing import Any, Dict
from uuid import UUID

import pytest

from slidetap.database.attribute import CodeAttribute, ObjectAttribute
from slidetap.database.project import Sample
from slidetap.model.code import Code
from slidetap.serialization import AttributeModel, ItemModelFactory


@pytest.mark.unittest
class TestSerialization:
    def test_dump_code(self, code_attribute: CodeAttribute):
        # Arrange

        # Act
        dumped = AttributeModel().dump(code_attribute)

        # Assert
        assert isinstance(code_attribute.value, Code)
        assert isinstance(dumped, dict)
        assert dumped["mappableValue"] == code_attribute.mappable_value
        assert UUID(dumped["uid"]) == code_attribute.uid
        assert dumped["value"]["code"] == code_attribute.value.code
        assert dumped["value"]["scheme"] == code_attribute.value.scheme
        assert dumped["value"]["meaning"] == code_attribute.value.meaning
        assert dumped["value"]["schemeVersion"] == code_attribute.value.scheme_version
        assert dumped["schema"]["tag"] == code_attribute.tag
        assert dumped["schema"]["displayName"] == code_attribute.schema_display_name
        assert UUID(dumped["schema"]["uid"]) == code_attribute.schema_uid
        assert (
            dumped["schema"]["attributeValueType"]
            == code_attribute.attribute_value_type.value
        )

    def test_load_code(
        self, code_attribute: CodeAttribute, dumped_code_attribute: Dict[str, Any]
    ):
        # Arrange
        # Act
        loaded = AttributeModel().load(dumped_code_attribute)

        # Assert
        assert isinstance(code_attribute.value, Code)
        assert isinstance(loaded, Dict)
        assert isinstance(loaded["value"], Code)
        assert loaded["mappable_value"] == code_attribute.mappable_value
        assert loaded["uid"] == code_attribute.uid
        assert loaded["value"].code == code_attribute.value.code
        assert loaded["value"].scheme == code_attribute.value.scheme
        assert loaded["value"].meaning == code_attribute.value.meaning
        assert loaded["value"].scheme_version == code_attribute.value.scheme_version
        assert loaded["schema"]["uid"] == code_attribute.schema_uid

    def test_dump_object_attribute(self, object_attribute: ObjectAttribute):
        # Arrange

        # Act
        dumped = AttributeModel().dump(object_attribute)

        # Assert
        assert isinstance(dumped, dict)

        assert dumped["mappableValue"] == object_attribute.mappable_value
        assert UUID(dumped["uid"]) == object_attribute.uid
        assert dumped["schema"]["tag"] == object_attribute.tag
        assert dumped["schema"]["displayName"] == object_attribute.schema_display_name
        assert UUID(dumped["schema"]["uid"]) == object_attribute.schema_uid
        assert (
            dumped["schema"]["attributeValueType"]
            == object_attribute.attribute_value_type.value
        )
        assert isinstance(dumped["value"], dict)
        for (tag, value), attribute in zip(
            dumped["value"].items(), object_attribute.attributes.values()
        ):
            assert isinstance(attribute.value, Code)
            assert tag == attribute.tag
            assert UUID(value["uid"]) == attribute.uid
            assert value["value"]["code"] == attribute.value.code
            assert value["value"]["scheme"] == attribute.value.scheme
            assert value["value"]["meaning"] == attribute.value.meaning
            assert value["value"]["schemeVersion"] == attribute.value.scheme_version
            assert value["schema"]["tag"] == attribute.tag
            assert value["schema"]["displayName"] == attribute.schema_display_name
            assert UUID(value["schema"]["uid"]) == attribute.schema_uid
            assert (
                value["schema"]["attributeValueType"]
                == attribute.attribute_value_type.value
            )

    def test_load_object_attribute(
        self, object_attribute: ObjectAttribute, dumped_object_attribute: Dict[str, Any]
    ):
        # Arrange

        # Act
        loaded = AttributeModel().load(dumped_object_attribute)

        # Assert
        assert isinstance(loaded, Dict)
        assert loaded["mappable_value"] == object_attribute.mappable_value
        assert loaded["uid"] == object_attribute.uid
        assert loaded["schema"]["uid"] == object_attribute.schema_uid
        assert isinstance(loaded["value"], dict)
        for (tag, value), attribute in zip(
            loaded["value"].items(), object_attribute.attributes.values()
        ):
            assert tag == attribute.tag
            loaded_value = value["value"]
            assert isinstance(attribute.value, Code)
            assert isinstance(loaded_value, Code)
            assert value["uid"] == attribute.uid
            assert loaded_value.code == attribute.value.code
            assert loaded_value.scheme == attribute.value.scheme
            assert loaded_value.meaning == attribute.value.meaning
            assert loaded_value.scheme_version == attribute.value.scheme_version
            assert value["schema"]["uid"] == attribute.schema_uid

    def test_sample_dump_simplified(self, block: Sample):
        # Arrange

        # Act
        model = ItemModelFactory().create_simplified(block.schema)
        dumped = model().dump(block)

        # Assert
        assert isinstance(dumped, dict)
        assert UUID(dumped["uid"]) == block.uid
        assert dumped["schema"]["displayName"] == block.schema_display_name
        assert dumped["selected"] == block.selected
        for dumped_parent, parent in zip(dumped["parents"], block.parents):
            assert UUID(dumped_parent["uid"]) == parent.uid
            assert dumped_parent["name"] == parent.name
            assert dumped_parent["schemaDisplayName"] == parent.schema_display_name
            assert UUID(dumped_parent["schemaUid"]) == parent.schema_uid

        for dumped_child, child in zip(dumped["children"], block.children):
            assert UUID(dumped_child["uid"]) == child.uid
            assert dumped_child["name"] == child.name
            assert dumped_child["schemaDisplayName"] == child.schema_display_name
            assert UUID(dumped_child["schemaUid"]) == child.schema_uid

        assert isinstance(dumped["attributes"], dict)
        for (tag, value), attribute in zip(
            dumped["attributes"].items(), block.attributes.values()
        ):
            assert isinstance(attribute.value, Code)
            assert tag == attribute.tag
            assert UUID(value["uid"]) == attribute.uid
            assert value["schema"]["displayName"] == attribute.schema_display_name
            assert value["displayValue"] == attribute.display_value

    def test_sample_dump(self, block: Sample):
        # Arrange

        # Act
        model = ItemModelFactory().create(block.schema)
        dumped = model().dump(block)

        # Assert
        assert isinstance(dumped, dict)
        assert UUID(dumped["uid"]) == block.uid
        assert dumped["schema"]["displayName"] == block.schema_display_name
        assert dumped["selected"] == block.selected
        for dumped_parent, parent in zip(dumped["parents"], block.parents):
            assert UUID(dumped_parent["uid"]) == parent.uid
            assert dumped_parent["name"] == parent.name
            assert dumped_parent["schemaDisplayName"] == parent.schema_display_name
            assert UUID(dumped_parent["schemaUid"]) == parent.schema_uid

        for dumped_child, child in zip(dumped["children"], block.children):
            assert UUID(dumped_child["uid"]) == child.uid
            assert dumped_child["name"] == child.name
            assert dumped_child["schemaDisplayName"] == child.schema_display_name
            assert UUID(dumped_child["schemaUid"]) == child.schema_uid

        assert isinstance(dumped["attributes"], dict)
        for (tag, value), attribute in zip(
            dumped["attributes"].items(), block.attributes.values()
        ):
            assert isinstance(attribute.value, Code)
            assert tag == attribute.tag
            assert UUID(value["uid"]) == attribute.uid
            assert value["schema"]["displayName"] == attribute.schema_display_name
            assert value["displayValue"] == attribute.display_value

    def test_sample_load(self, block: Sample, dumped_block: Dict[str, Any]):
        # Arrange

        # Act
        model = ItemModelFactory().create(block.schema)
        loaded = model().load(dumped_block)

        # Assert
        assert isinstance(loaded, dict)
        assert loaded["uid"] == block.uid
        assert loaded["selected"] == block.selected
        for loaded_parent, parent in zip(loaded["parents"], block.parents):
            assert loaded_parent["uid"] == parent.uid
            assert loaded_parent["schema_uid"] == parent.schema_uid

        for loaded_child, child in zip(loaded["children"], block.children):
            assert loaded_child["uid"] == child.uid
            assert loaded_child["schema_uid"] == child.schema_uid

        assert isinstance(loaded["attributes"], dict)
        for (tag, value), attribute in zip(
            loaded["attributes"].items(), block.attributes.values()
        ):
            assert isinstance(attribute.value, Code)
            assert tag == attribute.tag
            assert value["uid"] == attribute.uid
