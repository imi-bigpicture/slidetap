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

import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from uuid import uuid4

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
from slidetap.database.project import DatabaseBatch, DatabaseDataset
from slidetap.exporter import ImageExporter, MetadataExporter
from slidetap.importer import ImageImporter, MetadataImporter
from slidetap.model import (
    AttributeValueType,
    Batch,
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
    Image,
    ObjectAttribute,
    ObjectAttributeSchema,
    Project,
    RootSchema,
    Sample,
)
from slidetap.model.batch_status import BatchStatus
from slidetap.services.attribute_service import AttributeService
from slidetap.services.batch_service import BatchService
from slidetap.services.database_service import DatabaseService
from slidetap.services.dataset_service import DatasetService
from slidetap.services.mapper_service import MapperService
from slidetap.services.project_service import ProjectService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService
from slidetap.storage.storage import Storage
from slidetap.task.app_factory import TaskClassFactory
from slidetap.task.scheduler import Scheduler
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
    yield app


@pytest.fixture
def schema(app: Flask):
    yield ExampleSchema()


@pytest.fixture()
def dataset(schema: RootSchema):
    yield Dataset(
        uid=uuid4(),
        name="dataset name",
        schema_uid=schema.dataset.uid,
    )


@pytest.fixture()
def project(schema: RootSchema, dataset: Dataset):
    project = Project(
        uid=uuid4(),
        name="project name",
        root_schema_uid=schema.uid,
        schema_uid=schema.project.uid,
        dataset_uid=dataset.uid,
        created=datetime.datetime(2021, 1, 1),
    )
    yield project


@pytest.fixture()
def batch(project: Project):
    return Batch(
        uid=uuid4(),
        name="batch name",
        status=BatchStatus.INITIALIZED,
        project_uid=project.uid,
        is_default=True,
        created=datetime.datetime(2021, 1, 1),
    )


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
def block(schema: ExampleSchema, dataset: Dataset, batch: Batch):
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
        dataset_uid=dataset.uid,
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
def database_service(config: ExampleConfig):
    yield DatabaseService(config.database_uri)


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
def batch_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    database_service: DatabaseService,
):
    yield BatchService(validation_service, schema_service, database_service)


@pytest.fixture()
def dataset_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    database_service: DatabaseService,
):
    yield DatasetService(validation_service, schema_service, database_service)


@pytest.fixture()
def project_service(
    batch_service: BatchService,
    attribute_service: AttributeService,
    schema_service: SchemaService,
    validation_service: ValidationService,
    database_service: DatabaseService,
):
    yield ProjectService(
        attribute_service,
        batch_service,
        schema_service,
        validation_service,
        database_service,
    )


@pytest.fixture()
def image_importer(
    schema: ExampleSchema, scheduler: Scheduler, storage: Storage, config: ExampleConfig
):
    yield DummyImageImporter(schema, scheduler, config)


@pytest.fixture()
def image_exporter(
    schema: ExampleSchema, scheduler: Scheduler, storage: Storage, config: ExampleConfig
):
    yield DummyImageExporter(schema, scheduler, storage, config)


@pytest.fixture()
def metadata_importer(schema: ExampleSchema, scheduler: Scheduler, storage: Storage):
    yield DummyMetadataImporter(schema, scheduler)


@pytest.fixture()
def metadata_exporter(
    schema: ExampleSchema, scheduler: Scheduler, storage: Storage, config: ExampleConfig
):
    yield DummyMetadataExporter(schema, scheduler, storage, config)


@pytest.fixture()
def processing_service(
    image_importer: ImageImporter,
    image_exporter: ImageExporter,
    metadata_importer: MetadataImporter,
    metadata_exporter: MetadataExporter,
    project_service: ProjectService,
    dataset_service: DatasetService,
    batch_service: BatchService,
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
        dataset_service,
        batch_service,
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
def database_dataset(dataset: Dataset, schema: RootSchema):
    yield DatabaseDataset.create_from_model(dataset, schema.dataset)


@pytest.fixture()
def database_project(
    project: Project, schema: RootSchema, database_dataset: DatabaseDataset
):
    database_project = DatabaseProject.create_from_model(project, schema.project)
    database_project.dataset = database_dataset
    yield database_project


@pytest.fixture()
def database_batch(batch: Batch, database_project: DatabaseProject):
    yield DatabaseBatch.create_from_model(batch)
