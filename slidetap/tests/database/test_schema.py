from typing import List, Optional, Tuple
from uuid import uuid4

import pytest
from flask import Flask

from slidetap.database import (
    AnnotationSchema,
    BooleanAttributeSchema,
    CodeAttributeSchema,
    DatetimeAttributeSchema,
    EnumAttributeSchema,
    ImageSchema,
    ListAttributeSchema,
    MeasurementAttributeSchema,
    NumericAttributeSchema,
    ObjectAttributeSchema,
    ObservationSchema,
    SampleSchema,
    Schema,
    StringAttributeSchema,
    UnionAttributeSchema,
)
from slidetap.model import DatetimeType


@pytest.fixture
def schema(app: Flask):
    yield Schema.get_or_create(uuid4(), "Test schema")


@pytest.mark.unittest
class TestSlideTapDatabaseSchema:
    def test_create_schema(self, app: Flask):
        # Arrange
        name = "Test schema"
        uid = uuid4()

        # Act
        schema = Schema(uid, name)

        # Assert
        assert schema.name == name
        assert schema.uid == uid

    def test_get_or_create_schema(self, app: Flask):
        # Arrange
        name = "Test schema"
        uid = uuid4()

        # Act
        schema = Schema.get_or_create(uid, name)

        # Assert
        assert schema.name == name
        assert schema.uid == uid

    def test_get_or_create_schema_already_exists(self, app: Flask):
        # Arrange
        name = "Test schema"
        uid = uuid4()
        existing_schema = Schema.get_or_create(uid, name)

        # Act
        schema = Schema.get_or_create(uid, name)

        # Assert
        assert schema == existing_schema

    def test_get(self, app: Flask):
        # Arrange
        uid = uuid4()
        name = "Test schema"
        existing_schema = Schema.get_or_create(uid, "Existing")

        # Act
        schema = Schema.get(uid)

        # Assert
        assert schema == existing_schema

    def test_get_no_schema(self, app: Flask):
        # Arrange
        uid = uuid4()
        name = "Test schema"
        existing_schema = Schema.get_or_create(uuid4(), "Existing")

        # Act
        schema = Schema.get(uid)

        # Assert
        assert schema is None

    def test_create_sample_schema(self, schema: Schema):
        # Arrange
        child = SampleSchema.get_or_create(schema, "child", "Child", 0)
        attribute = StringAttributeSchema.get_or_create(
            schema, "attribute", "Attribute"
        )
        name = "sample"
        display_name = "Sample"

        # Act
        sample_schema = SampleSchema.get_or_create(
            schema, name, display_name, 0, [child], [attribute]
        )

        # Assert
        assert sample_schema.schema == schema
        assert sample_schema.name == name
        assert sample_schema.display_name == display_name
        assert sample_schema.children == [child]
        assert sample_schema.attributes == [attribute]

    def test_create_image_schema(self, schema: Schema):
        # Arrange
        sample = SampleSchema.get_or_create(schema, "sample", "Sample", 0)
        attribute = StringAttributeSchema.get_or_create(
            schema, "attribute", "Attribute"
        )
        name = "image"
        display_name = "Image"

        # Act
        image_schema = ImageSchema.get_or_create(
            schema, name, display_name, 0, [sample], [attribute]
        )

        # Assert
        assert image_schema.schema == schema
        assert image_schema.name == name
        assert image_schema.display_name == display_name
        assert image_schema.parents == [sample]
        assert image_schema.attributes == [attribute]

    def test_create_annotation_schema(self, schema: Schema):
        # Arrange
        image = ImageSchema.get_or_create(schema, "image", "Image", 0)
        attribute = StringAttributeSchema.get_or_create(
            schema, "attribute", "Attribute"
        )
        name = "annotation"
        display_name = "Annotation"

        # Act
        annotation_schema = AnnotationSchema.get_or_create(
            schema, name, display_name, 1, [image], [attribute]
        )

        # Assert
        assert annotation_schema.schema == schema
        assert annotation_schema.name == name
        assert annotation_schema.display_name == display_name
        assert annotation_schema.parents == [image]
        assert annotation_schema.attributes == [attribute]

    def test_create_observation_schema(self, schema: Schema):
        # Arrange
        image = ImageSchema.get_or_create(schema, "image", "Image", 0)
        attribute = StringAttributeSchema.get_or_create(
            schema, "attribute", "Attribute"
        )
        name = "observation"
        display_name = "Observation"

        # Act
        observation_schema = ObservationSchema.get_or_create(
            schema, name, display_name, 0, [image], [attribute]
        )

        # Assert
        assert observation_schema.schema == schema
        assert observation_schema.name == name
        assert observation_schema.display_name == display_name
        assert observation_schema.parents == [image]
        assert observation_schema.attributes == [attribute]

    def test_create_attribute_schema_already_exists_throws(self, schema: Schema):
        # Arrange
        existing_schema = CodeAttributeSchema.get_or_create(
            schema, "collection", "Collection method", "collection"
        )

        # Act & Assert
        with pytest.raises(Exception):
            duplicate_schema = CodeAttributeSchema(
                schema, existing_schema.name, "Collection method", "collection"
            )

    def test_create_string_attribute_schema(self, schema: Schema):
        # Arrange
        name = "test string attribute"
        display_name = "String"
        tag = "test_attribute"

        # Act
        attribute_schema = StringAttributeSchema.get_or_create(
            schema, name, display_name, tag
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag

    @pytest.mark.parametrize("allowed_values", [None, ["value 1", "value 2"]])
    def test_create_enum_attribute_schema(
        self, schema: Schema, allowed_values: Optional[List[str]]
    ):
        # Arrange
        name = "test enum attribute"
        display_name = "Enum"
        tag = "test_attribute"

        # Act
        attribute_schema = EnumAttributeSchema.get_or_create(
            schema, name, display_name, tag, allowed_values
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        assert attribute_schema.allowed_values == allowed_values

    @pytest.mark.parametrize(
        "datetime_type",
        [DatetimeType.TIME, DatetimeType.DATE, DatetimeType.DATETIME],
    )
    def test_create_datetime_attribute_schema(
        self, schema: Schema, datetime_type: DatetimeType
    ):
        # Arrange
        name = "test datetime attribute"
        display_name = "Datetime"
        tag = "test_attribute"

        # Act
        attribute_schema = DatetimeAttributeSchema.get_or_create(
            schema, name, display_name, tag, datetime_type
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        assert attribute_schema.datetime_type == datetime_type

    @pytest.mark.parametrize(
        "is_int",
        [False, True],
    )
    def test_create_numeric_attribute_schema(self, schema: Schema, is_int: bool):
        # Arrange
        name = "test numeric attribute"
        display_name = "Numeric"
        tag = "test_attribute"

        # Act
        attribute_schema = NumericAttributeSchema.get_or_create(
            schema, name, display_name, tag, is_int
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        assert attribute_schema.is_int == is_int

    @pytest.mark.parametrize("allowed_units", [None, ["unit 1", "unit 2"]])
    def test_create_measurement_attribute_schema(
        self, schema: Schema, allowed_units: Optional[List[str]]
    ):
        # Arrange
        name = "test measurement attribute"
        display_name = "Measurement"
        tag = "test_attribute"

        # Act
        attribute_schema = MeasurementAttributeSchema.get_or_create(
            schema, name, display_name, tag, allowed_units
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        assert attribute_schema.allowed_units == allowed_units

    @pytest.mark.parametrize("allowed_schemas", [None, ["schema 1", "schema 2"]])
    def test_create_code_attribute_schema(
        self, schema: Schema, allowed_schemas: Optional[List[str]]
    ):
        # Arrange
        name = "test code attribute"
        display_name = "Code"
        tag = "test_attribute"

        # Act
        attribute_schema = CodeAttributeSchema.get_or_create(
            schema, name, display_name, tag, allowed_schemas
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        assert attribute_schema.allowed_schemas == allowed_schemas

    @pytest.mark.parametrize("display_values", [None, ("Yes", "No")])
    def test_create_boolean_attribute_schema(
        self, schema: Schema, display_values: Optional[Tuple[str, str]]
    ):
        # Arrange
        name = "test boolean attribute"
        display_name = "Bool"
        tag = "test_attribute"

        # Act
        attribute_schema = BooleanAttributeSchema.get_or_create(
            schema, name, display_name, tag, display_values
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        if display_values is None:
            assert attribute_schema.true_display_value is None
            assert attribute_schema.false_display_value is None
        else:
            assert attribute_schema.true_display_value == display_values[0]
            assert attribute_schema.false_display_value == display_values[1]

    def test_create_object_attribute_schema(self, schema: Schema):
        # Arrange
        name = "test object attribute"
        display_name = "Object"
        tag = "test_attribute"
        child_attribute_1 = StringAttributeSchema.get_or_create(
            schema, "child 1", "Child 1"
        )
        child_attribute_2 = StringAttributeSchema.get_or_create(
            schema, "child 2", "Child 2"
        )

        # Act
        attribute_schema = ObjectAttributeSchema.get_or_create(
            schema, name, display_name, [child_attribute_1, child_attribute_2], tag
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        assert attribute_schema.attributes is not None
        assert child_attribute_1 in attribute_schema.attributes
        assert child_attribute_2 in attribute_schema.attributes

    def test_create_list_attribute_schema(self, schema: Schema):
        # Arrange
        name = "test list attribute"
        display_name = "List"
        tag = "test_attribute"
        listed_attribute = StringAttributeSchema.get_or_create(schema, "listed", "List")

        # Act
        attribute_schema = ListAttributeSchema.get_or_create(
            schema, name, display_name, listed_attribute, tag
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        assert attribute_schema.attribute == listed_attribute

    def test_create_union_attribute_schema(self, schema: Schema):
        # Arrange
        name = "test union attribute"
        display_name = "Union"
        tag = "test_attribute"
        string_attribute = StringAttributeSchema.get_or_create(schema, "listed", "List")
        bool_attribute = BooleanAttributeSchema.get_or_create(schema, "bool", "Union")
        attributes = [string_attribute, bool_attribute]

        # Act
        attribute_schema = UnionAttributeSchema.get_or_create(
            schema, name, display_name, attributes, tag
        )

        # Assert
        assert attribute_schema.schema == schema
        assert attribute_schema.name == name
        assert attribute_schema.display_name == display_name
        assert attribute_schema.tag == tag
        for attribute in attributes:
            assert attribute in attribute_schema.attributes
