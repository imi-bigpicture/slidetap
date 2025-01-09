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

from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import List, Sequence
from uuid import UUID, uuid4

import pytest
from flask import Flask
from slidetap.apps.example.config import ExampleConfig, ExampleConfigTest
from slidetap.apps.example.processors.processor_factory import (
    ExampleImageDownloaderFactory,
    ExampleImagePostProcessorFactory,
    ExampleImagePreProcessorFactory,
    ExampleMetadataExportProcessorFactory,
    ExampleMetadataImportProcessorFactory,
)
from slidetap.apps.example.schema import ExampleSchema
from slidetap.database import DatabaseProject, db
from slidetap.model import Code, CodeAttributeSchema, Image, Project, RootSchema, Sample
from slidetap.model.attribute import CodeAttribute, ObjectAttribute
from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.schema.attribute_schema import ObjectAttributeSchema
from slidetap.services import (
    AttributeService,
    MapperService,
    ProjectService,
    SchemaService,
    ValidationService,
)
from slidetap.services.database_service import DatabaseService
from slidetap.storage.storage import Storage
from slidetap.task.app_factory import TaskClassFactory
from slidetap.task.scheduler import Scheduler
from slidetap.web.exporter import ImageExporter, MetadataExporter
from slidetap.web.importer import ImageImporter, MetadataImporter
from slidetap.web.processing_service import ProcessingService

from tests.test_classes.image_exporter import DummyImageExporter
from tests.test_classes.image_importer import DummyImageImporter
from tests.test_classes.metadata_exporter import DummyMetadataExporter
from tests.test_classes.metadata_importer import DummyMetadataImporter


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}
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
    yield ExampleSchema()


@pytest.fixture()
def project(schema: RootSchema):
    project = Project(uuid4(), "project name", schema.project.uid)
    yield project


def create_sample(schema: ExampleSchema, project: Project, identifier="specimen 1"):
    sample_schema = schema.specimen
    return Sample(
        uuid4(),
        identifier,
        project_uid=project.uid,
        schema_uid=sample_schema.uid,
    )


def create_slide(
    schema: ExampleSchema,
    project: Project,
    parents: Sequence[UUID],
    identifier="slide 1",
):
    sample_schema = schema.slide
    return Sample(
        uuid4(),
        identifier,
        project_uid=project.uid,
        schema_uid=sample_schema.uid,
        parents=list(parents),
    )


def create_image(
    schema: ExampleSchema,
    project: Project,
    samples: List[UUID],
    identifier="image 1",
):
    image_schema = next(
        image for image in schema.images.values() if image.name == "wsi"
    )
    return Image(
        uuid4(),
        identifier,
        project_uid=project.uid,
        schema_uid=image_schema.uid,
        samples=samples,
    )


@pytest.fixture()
def sample(schema: ExampleSchema, project: Project):
    yield create_sample(schema, project)


@pytest.fixture()
def image(schema: ExampleSchema, project: Project, sample: Sample):
    yield create_image(schema, project, [sample.uid])


@pytest.fixture()
def slide(schema: ExampleSchema, project: Project, sample: Sample):
    yield create_slide(schema, project, [sample.uid])


@pytest.fixture()
def code_attribute_schema(schema: ExampleSchema):
    yield schema.specimen.attributes["collection"]


@pytest.fixture()
def code_attribute(code_attribute_schema: CodeAttributeSchema):
    return CodeAttribute(
        uuid4(), code_attribute_schema.uid, Code("code", "scheme", "meaning")
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
        uuid4(),
        "fixation",
        "fixation",
        "Fixation",
        optional=False,
        read_only=False,
        display_in_table=False,
    )
    collection_schema = CodeAttributeSchema(
        uuid4(),
        "collection",
        "collection",
        "Collection method",
        optional=False,
        read_only=False,
        display_in_table=False,
    )
    yield ObjectAttributeSchema(
        uuid4(),
        "test",
        "test",
        "Test",
        optional=False,
        read_only=False,
        display_in_table=True,
        display_attributes_in_parent=True,
        display_value_format_string=None,
        attributes=MappingProxyType(
            {"fixation": fixation_schema, "collection": collection_schema}
        ),
    )


@pytest.fixture()
def object_attribute(object_attribute_schema: ObjectAttributeSchema):
    collection = CodeAttribute(
        uuid4(),
        object_attribute_schema.attributes["collection"].uid,
        Code("collection code", "collection scheme", "collection meaning"),
    )
    fixation = CodeAttribute(
        uuid4(),
        object_attribute_schema.attributes["fixation"].uid,
        Code("fixation code", "fixation scheme", "fixation meaning"),
    )
    yield ObjectAttribute(
        uuid4(),
        object_attribute_schema.uid,
        {"collection": collection, "fixation": fixation},
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


@pytest.fixture()
def block(schema: ExampleSchema, project: Project):
    embedding = CodeAttribute(
        uuid4(),
        schema.block.attributes["embedding"].uid,
        Code("embedding code", "embedding scheme", "embedding meaning"),
    )
    block_sampling = CodeAttribute(
        uuid4(),
        schema.block.attributes["block_sampling"].uid,
        Code("block sampling code", "block sampling scheme", "block sampling meaning"),
    )
    yield Sample(
        uuid4(),
        "block 1",
        project_uid=project.uid,
        schema_uid=schema.block.uid,
        children=[uuid4()],
        parents=[uuid4()],
        attributes={"embedding": embedding, "block_sampling": block_sampling},
    )


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
        "projectUid": block.project_uid,
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
        "parents": [str(parent) for parent in block.parents],
        "children": [str(child) for child in block.children],
        "name": "block 1",
        "schemaUid": str(block.schema_uid),
        "images": [],
        "observations": [],
    }


@pytest.fixture
def storage_path():
    with TemporaryDirectory() as storage_dir:
        yield Path(storage_dir)


@pytest.fixture()
def storage(storage_path: Path):
    yield Storage(storage_path)


@pytest.fixture()
def config(storage_path: Path):
    yield ExampleConfigTest(storage_path, storage_path)


@pytest.fixture()
def scheduler(config: ExampleConfig):
    yield Scheduler()


@pytest.fixture()
def schema_service(schema: RootSchema):
    yield SchemaService(schema)


@pytest.fixture()
def database_service():
    yield DatabaseService()


@pytest.fixture()
def validation_service(
    schema_service: SchemaService, database_service: DatabaseService
):
    yield ValidationService(schema_service, database_service)


@pytest.fixture()
def attribute_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    database_service: DatabaseService,
):
    yield AttributeService(schema_service, validation_service, database_service)


@pytest.fixture()
def project_service(
    attribute_service: AttributeService,
    schema_service: SchemaService,
    validation_service: ValidationService,
    database_service: DatabaseService,
):
    yield ProjectService(
        attribute_service, schema_service, validation_service, database_service
    )


@pytest.fixture()
def image_importer(schema: ExampleSchema, scheduler: Scheduler, storage: Storage):
    yield DummyImageImporter(schema, scheduler)


@pytest.fixture()
def image_exporter(schema: ExampleSchema, scheduler: Scheduler, storage: Storage):
    yield DummyImageExporter(schema, scheduler, storage)


@pytest.fixture()
def metadata_importer(schema: ExampleSchema, scheduler: Scheduler, storage: Storage):
    yield DummyMetadataImporter(schema, scheduler)


@pytest.fixture()
def metadata_exporter(schema: ExampleSchema, scheduler: Scheduler, storage: Storage):
    yield DummyMetadataExporter(schema, scheduler, storage)


@pytest.fixture()
def processing_service(
    image_importer: ImageImporter,
    image_exporter: ImageExporter,
    metadata_importer: MetadataImporter,
    metadata_exporter: MetadataExporter,
    project_service: ProjectService,
    schema_service: SchemaService,
    validation_service: ValidationService,
    database_service: DatabaseService,
):
    yield ProcessingService(
        image_importer,
        image_exporter,
        metadata_importer,
        metadata_exporter,
        project_service,
        schema_service,
        validation_service,
        database_service,
    )


@pytest.fixture()
def mapper_service(
    validation_service: ValidationService, database_service: DatabaseService
):
    yield MapperService(validation_service, database_service)


@pytest.fixture()
def celery_task_class_factory(config: ExampleConfig, schema: RootSchema):
    yield TaskClassFactory(
        image_downloader_factory=ExampleImageDownloaderFactory(config, schema),
        image_pre_processor_factory=ExampleImagePreProcessorFactory(config, schema),
        image_post_processor_factory=ExampleImagePostProcessorFactory(config, schema),
        metadata_export_processor_factory=ExampleMetadataExportProcessorFactory(
            config, schema
        ),
        metadata_import_processor_factory=ExampleMetadataImportProcessorFactory(
            config, schema
        ),
    )


@pytest.fixture()
def project_schema(schema: RootSchema):
    yield schema.project


@pytest.fixture()
def database_project(project: Project, schema: RootSchema):
    yield DatabaseProject.get_or_create_from_model(project, schema.project)
