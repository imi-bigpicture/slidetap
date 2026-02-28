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
from uuid import UUID, uuid4

import pytest
from slidetap.model import (
    AttributeValueType,
    Batch,
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
    ObjectAttribute,
    ObjectAttributeSchema,
    Sample,
)
from slidetap_example.schema import ExampleSchema


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
def dumped_code_attribute(code_attribute: CodeAttribute):
    yield {
        "originalValue": {
            "meaning": "meaning",
            "scheme": "scheme",
            "schemeVersion": None,
            "code": "code",
        },
        "schemaUid": str(code_attribute.schema_uid),
        "attributeValueType": AttributeValueType.CODE.value,
        "mappableValue": None,
        "uid": str(code_attribute.uid),
    }


@pytest.fixture()
def object_attribute_schema():
    fixation_schema = CodeAttributeSchema(
        uid=uuid4(),
        tag="fixation",
        name="fixation",
        display_name="Fixation",
        optional=False,
        read_only=False,
        display_in_table=False,
    )
    collection_schema = CodeAttributeSchema(
        uid=uuid4(),
        tag="collection",
        name="collection",
        display_name="Collection method",
        optional=False,
        read_only=False,
        display_in_table=False,
    )

    yield ObjectAttributeSchema(
        uid=uuid4(),
        tag="test",
        name="test",
        display_name="Test",
        optional=False,
        read_only=False,
        display_in_table=True,
        display_attributes_in_parent=True,
        attributes={"fixation": fixation_schema, "collection": collection_schema},
        display_value_tags=["collection", "fixation"],
    )


@pytest.fixture()
def object_attribute(object_attribute_schema: ObjectAttributeSchema):
    collection = CodeAttribute(
        uid=uuid4(),
        schema_uid=object_attribute_schema.attributes["collection"].uid,
        original_value=Code(
            code="collection code",
            scheme="collection scheme",
            meaning="collection meaning",
        ),
    )
    fixation = CodeAttribute(
        uid=uuid4(),
        schema_uid=object_attribute_schema.attributes["fixation"].uid,
        original_value=Code(
            code="fixation code", scheme="fixation scheme", meaning="fixation meaning"
        ),
    )
    yield ObjectAttribute(
        uid=uuid4(),
        schema_uid=object_attribute_schema.uid,
        original_value={"collection": collection, "fixation": fixation},
        updated_value=None,
        mapped_value=None,
    )


@pytest.fixture()
def block(schema: ExampleSchema, dataset: Dataset, batch: Batch):
    embedding = CodeAttribute(
        uid=uuid4(),
        schema_uid=schema.block.attributes["embedding"].uid,
        original_value=Code(
            code="embedding code",
            scheme="embedding scheme",
            meaning="embedding meaning",
        ),
    )
    block_sampling = CodeAttribute(
        uid=uuid4(),
        schema_uid=schema.block.attributes["block_sampling"].uid,
        original_value=Code(
            code="block sampling code",
            scheme="block sampling scheme",
            meaning="block sampling meaning",
        ),
    )
    yield Sample(
        uid=uuid4(),
        identifier="block 1",
        dataset_uid=dataset.uid,
        schema_uid=schema.block.uid,
        name="block 1",
        external_identifier=None,
        pseudonym=None,
        selected=True,
        valid=None,
        valid_attributes=None,
        valid_relations=None,
        attributes={"embedding": embedding, "block_sampling": block_sampling},
        batch_uid=batch.uid,
        parents={schema.specimen.uid: [uuid4()]},
        children={},
        images={},
        observations={},
    )


@pytest.fixture()
def dumped_object_attribute(object_attribute: ObjectAttribute):
    value = next(
        attribute_value
        for attribute_value in [
            object_attribute.original_value,
            object_attribute.updated_value,
            object_attribute.mapped_value,
        ]
        if attribute_value is not None
    )
    yield {
        "uid": str(object_attribute.uid),
        "schemaUid": str(object_attribute.schema_uid),
        "originalValue": {
            "collection": {
                "uid": str(value["collection"].uid),
                "schemaUid": str(value["collection"].schema_uid),
                "originalValue": {
                    "scheme": "collection scheme",
                    "code": "collection code",
                    "schemeVersion": None,
                    "meaning": "collection meaning",
                },
                "attributeValueType": AttributeValueType.CODE.value,
                "mappableValue": None,
            },
            "fixation": {
                "uid": str(value["fixation"].uid),
                "schemaUid": str(value["fixation"].schema_uid),
                "originalValue": {
                    "scheme": "fixation scheme",
                    "code": "fixation code",
                    "schemeVersion": None,
                    "meaning": "fixation meaning",
                },
                "attributeValueType": AttributeValueType.CODE.value,
                "mappableValue": None,
            },
        },
        "updatedValue": None,
        "mappedValue": None,
        "valid": True,
        "dispalyValue": None,
        "mappingValue": None,
        "mappingItemUid": None,
        "attributeValueType": AttributeValueType.OBJECT.value,
    }


@pytest.fixture
def dumped_block(block: Sample):
    embedding = block.attributes["embedding"]
    assert isinstance(embedding, CodeAttribute)
    assert embedding.original_value is not None
    block_sampling = block.attributes["block_sampling"]
    assert isinstance(block_sampling, CodeAttribute)
    assert block_sampling.original_value is not None
    yield {
        "uid": str(block.uid),
        "identifier": block.identifier,
        "datasetUid": block.dataset_uid,
        "batchUid": block.batch_uid,
        "attributes": {
            "embedding": {
                "uid": str(embedding.uid),
                "originalValue": {
                    "schemeVersion": embedding.original_value.scheme_version,
                    "code": embedding.original_value.code,
                    "meaning": embedding.original_value.meaning,
                    "scheme": embedding.original_value.scheme,
                },
                "schemaUid": str(embedding.schema_uid),
                "attributeValueType": AttributeValueType.CODE.value,
                "mappableValue": None,
            },
            "block_sampling": {
                "uid": str(block_sampling.uid),
                "originalValue": {
                    "schemeVersion": block_sampling.original_value.scheme_version,
                    "code": block_sampling.original_value.code,
                    "meaning": block_sampling.original_value.meaning,
                    "scheme": block_sampling.original_value.scheme,
                },
                "schemaUid": str(block_sampling.schema_uid),
                "attributeValueType": AttributeValueType.CODE.value,
                "mappableValue": None,
            },
        },
        "selected": True,
        "parents": {
            str(parent_schema_uid): [str(parent) for parent in parents]
            for parent_schema_uid, parents in block.parents.items()
        },
        "children": {
            str(child_schema_uid): [str(child) for child in children]
            for child_schema_uid, children in block.children.items()
        },
        "name": "block 1",
        "schemaUid": str(block.schema_uid),
        "images": {},
        "observations": {},
    }


@pytest.mark.unittest
class TestSerialization:
    def test_dump_code(self, code_attribute: CodeAttribute):
        # Arrange

        # Act
        dumped = code_attribute.model_dump(mode="json", by_alias=True)

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
        loaded = CodeAttribute.model_validate(dumped_code_attribute)

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
        dumped = object_attribute.model_dump(mode="json", by_alias=True)

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
        loaded = ObjectAttribute.model_validate(dumped_object_attribute)

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

        # Act
        dumped = block.model_dump(mode="json", by_alias=True)

        # Assert
        assert isinstance(dumped, dict)
        assert dumped["uid"] == str(block.uid)
        assert dumped["selected"] == block.selected
        assert dumped["parents"] == {
            str(parent_schema_uid): [str(parent) for parent in parents]
            for parent_schema_uid, parents in block.parents.items()
        }
        assert dumped["children"] == {
            str(child_schema_uid): [str(child) for child in children]
            for child_schema_uid, children in block.children.items()
        }
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

        # Act
        loaded = block.model_validate(dumped_block)

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
