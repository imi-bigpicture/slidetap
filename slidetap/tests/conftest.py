from typing import List, Sequence
from uuid import uuid4

import pytest
from flask import Flask

from slidetap.apps.example import ExampleSchema
from slidetap.database import (
    CodeAttribute,
    CodeAttributeSchema,
    Image,
    ImageSchema,
    ListAttribute,
    ListAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    Project,
    Sample,
    SampleSchema,
    Schema,
    db,
)
from slidetap.model import Code


@pytest.fixture
def sql_alchemy_database_uri():
    return "sqlite:///:memory:"


@pytest.fixture
def app(sql_alchemy_database_uri: str):
    app = Flask(__name__)
    app.config.update(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": sql_alchemy_database_uri}
    )
    with app.app_context():
        db.init_app(app)
        db.create_all()
    app.app_context().push()
    yield app

    with app.app_context():
        db.session.close()
        db.drop_all()


@pytest.fixture
def schema(app: Flask):
    yield ExampleSchema.create()


@pytest.fixture()
def project(app: Flask):
    schema = Schema(uuid4(), "test")
    SampleSchema.get_or_create(schema, "Case", "Case", 0)
    ImageSchema.get_or_create(schema, "WSI", "wsi", 2)
    project = Project("project name", schema)
    yield project


def create_sample(project: Project, name="case 1"):
    sample_schema = SampleSchema.get_or_create(project.schema, "Case", "Case", 0)
    return Sample(project, name, sample_schema)


def create_slide(project: Project, parents: Sequence[Sample], name="slide 1"):
    sample_schema = SampleSchema.get_or_create(project.schema, "Slide", "Slide", 1)
    return Sample(project, name, sample_schema, parents)


def create_image(project: Project, samples: List[Sample], name="image 1"):
    image_schema = ImageSchema.get_or_create(project.schema, "WSI", "wsi", 2)
    return Image(project, name, image_schema, samples)


@pytest.fixture()
def sample(project: Project):
    yield create_sample(project)


@pytest.fixture()
def image(project: Project, sample: Sample):
    yield create_image(project, [sample])


@pytest.fixture()
def slide(project: Project, sample: Sample):
    yield create_slide(project, [sample])


@pytest.fixture()
def code_attribute(schema: Schema):
    collection_schema = CodeAttributeSchema.get_or_create(
        schema, "collection", "Collection method", "collection"
    )
    yield CodeAttribute(collection_schema, Code("code", "scheme", "meaning"))


@pytest.fixture()
def dumped_code_attribute(code_attribute: CodeAttribute):
    yield {
        "value": {
            "meaning": "meaning",
            "scheme": "scheme",
            "schemeVersion": None,
            "code": "code",
        },
        "schema": {
            "uid": str(code_attribute.schema_uid),
        },
        "mappableValue": None,
        "uid": str(code_attribute.uid),
    }


@pytest.fixture()
def object_attribute(schema: Schema):
    fixation_schema = CodeAttributeSchema.get_or_create(schema, "fixation", "Fixation")
    collection_schema = CodeAttributeSchema.get_or_create(
        schema, "collection", "Collection method", "collection"
    )
    object_schema = ObjectAttributeSchema(
        schema, "test", "display name", [fixation_schema, collection_schema]
    )
    collection = CodeAttribute(
        collection_schema,
        Code("collection code", "collection scheme", "collection meaning"),
    )
    fixation = CodeAttribute(
        fixation_schema,
        Code("fixation code", "fixation scheme", "fixation meaning"),
    )
    yield ObjectAttribute(
        object_schema,
        [collection, fixation],
    )


@pytest.fixture()
def dumped_object_attribute(object_attribute: ObjectAttribute):
    yield {
        "schema": {
            "uid": str(object_attribute.schema.uid),
        },
        "value": {
            "collection": {
                "schema": {
                    "uid": str(object_attribute.attributes["collection"].schema_uid),
                },
                "value": {
                    "scheme": "collection scheme",
                    "code": "collection code",
                    "schemeVersion": None,
                    "meaning": "collection meaning",
                },
                "uid": str(object_attribute.attributes["collection"].uid),
                "mappableValue": None,
            },
            "fixation": {
                "schema": {
                    "uid": str(object_attribute.attributes["fixation"].schema_uid),
                },
                "value": {
                    "scheme": "fixation scheme",
                    "code": "fixation code",
                    "schemeVersion": None,
                    "meaning": "fixation meaning",
                },
                "uid": str(object_attribute.attributes["fixation"].uid),
            },
        },
        "uid": str(object_attribute.uid),
        "mappableValue": None,
    }


@pytest.fixture()
def block(schema: Schema, project: Project):
    fixation_schema = CodeAttributeSchema.get_or_create(schema, "fixation", "Fixation")
    collection_schema = CodeAttributeSchema.get_or_create(
        schema, "collection", "Collection method"
    )
    specimen_schema = SampleSchema.get_or_create(
        schema,
        "specimen",
        "Specimen",
        0,
        attributes=[fixation_schema, collection_schema],
    )

    sampling_method_schema = CodeAttributeSchema.get_or_create(
        schema, "block_sampling", "Sampling method"
    )
    embedding_schema = CodeAttributeSchema.get_or_create(
        schema,
        "embedding",
        "Embedding",
    )

    block_schema = SampleSchema.get_or_create(
        schema,
        "block",
        "Block",
        1,
        [specimen_schema],
        [embedding_schema, sampling_method_schema],
    )
    stain_schema = CodeAttributeSchema.get_or_create(schema, "stain", "Stain")
    staining_schema = ListAttributeSchema.get_or_create(
        schema, "staining", "Staining", stain_schema
    )

    slide_schema = SampleSchema.get_or_create(
        schema, "slide", "Slide", 2, [block_schema], [staining_schema]
    )

    collection = CodeAttribute(
        collection_schema,
        Code("collection code", "collection scheme", "collection meaning"),
    )
    fixation = CodeAttribute(
        fixation_schema,
        Code("fixation code", "fixation scheme", "fixation meaning"),
    )
    specimen = Sample(
        project, "specimen 1", specimen_schema, [], [collection, fixation]
    )
    sampling_method = CodeAttribute(
        sampling_method_schema,
        Code(
            "sampling method code",
            "sampling method scheme",
            "sampling method meaning",
        ),
    )
    embedding = CodeAttribute(
        embedding_schema,
        Code("embedding code", "embedding scheme", "embedding meaning"),
    )
    block = Sample(
        project, "block 1", block_schema, [specimen], [sampling_method, embedding]
    )
    stain = CodeAttribute(
        stain_schema,
        Code("stain code", "stain scheme", "stain meaning"),
    )
    staining = ListAttribute(staining_schema, [stain])
    slide = Sample(project, "slide 1", slide_schema, [block], [staining])
    yield block


@pytest.fixture
def dumped_block(block: Sample):
    yield {
        "uid": str(block.uid),
        "attributes": {
            "block_sampling": {
                "uid": str(block.attributes["block_sampling"].uid),
                "value": {
                    "schemeVersion": None,
                    "code": "sampling method code",
                    "meaning": "sampling method meaning",
                    "scheme": "sampling method scheme",
                },
                "schema": {
                    "uid": str(block.attributes["block_sampling"].schema_uid),
                    "name": block.attributes["block_sampling"].schema.name,
                    "displayName": block.attributes[
                        "block_sampling"
                    ].schema_display_name,
                },
                "mappableValue": None,
            },
            "embedding": {
                "uid": str(block.attributes["embedding"].uid),
                "value": {
                    "schemeVersion": None,
                    "code": "embedding code",
                    "meaning": "embedding meaning",
                    "scheme": "embedding scheme",
                },
                "schema": {
                    "uid": str(block.attributes["embedding"].schema_uid),
                    "name": block.attributes["embedding"].schema.name,
                    "displayName": block.attributes["embedding"].schema_display_name,
                },
                "mappableValue": None,
            },
        },
        "selected": True,
        "parents": [
            {
                "uid": str(block.parents[0].uid),
                "schemaUid": str(block.parents[0].schema_uid),
            }
        ],
        "name": "block 1",
        "schema": {
            "uid": str(block.schema_uid),
            "schemaUid": str(block.schema.schema_uid),
            "name": block.schema.name,
            "displayName": block.schema_display_name,
        },
        "children": [
            {
                "uid": str(block.children[0].uid),
                "schemaUid": str(block.children[0].schema_uid),
            }
        ],
    }
