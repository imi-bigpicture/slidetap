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
from types import MappingProxyType
from uuid import uuid4

import pytest
from flask import Flask
from slidetap import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.apps.example.config import ExampleConfig, ExampleConfigTest
from slidetap.apps.example.interfaces.image_export import ExampleImageExportInterface
from slidetap.apps.example.interfaces.image_import import ExampleImageImportInterface
from slidetap.apps.example.interfaces.metadata_export import (
    ExampleMetadataExportInterface,
)
from slidetap.apps.example.interfaces.metadata_import import (
    ExampleMetadataImportInterface,
)
from slidetap.apps.example.schema import ExampleSchema
from slidetap.config import Config
from slidetap.model import (
    AttributeValueType,
    Batch,
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
    ObjectAttribute,
    ObjectAttributeSchema,
    Project,
    RootSchema,
    Sample,
)
from slidetap.model.batch_status import BatchStatus
from slidetap.service_provider import ServiceProvider
from slidetap.task import Scheduler
from slidetap.task.app_factory import SlideTapTaskAppFactory
from slidetap.web.services.image_export_service import ImageExportService
from slidetap.web.services.image_import_service import ImageImportService
from slidetap.web.services.metadata_export_service import MetadataExportService
from slidetap.web.services.metadata_import_service import MetadataImportService


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update({"TESTING": True})
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


@pytest.fixture()
def config(tmpdir: str):
    yield ExampleConfigTest(Path(tmpdir))


@pytest.fixture()
def scheduler(config: ExampleConfig):
    yield Scheduler()


@pytest.fixture
def service_provider(config: Config, schema: RootSchema):
    return ServiceProvider(config, schema)


@pytest.fixture()
def database_service(service_provider: ServiceProvider):
    yield service_provider.database_service


@pytest.fixture()
def metadata_import_interface(service_provider: ServiceProvider):
    yield ExampleMetadataImportInterface(service_provider)


@pytest.fixture()
def metadata_export_interface(service_provider: ServiceProvider):
    yield ExampleMetadataExportInterface(service_provider)


@pytest.fixture()
def image_import_interface(config: ExampleConfig):
    yield ExampleImageImportInterface(config)


@pytest.fixture()
def image_export_interface(service_provider: ServiceProvider, config: ExampleConfig):
    yield ExampleImageExportInterface(service_provider, config)


@pytest.fixture()
def metadata_import_service(
    scheduler: Scheduler,
    metadata_import_interface: MetadataImportInterface,
):
    yield MetadataImportService(
        scheduler,
        metadata_import_interface,
    )


@pytest.fixture()
def metadata_export_service(
    scheduler: Scheduler,
    service_provider: ServiceProvider,
    metadata_export_interface: MetadataExportInterface,
):
    yield MetadataExportService(
        scheduler,
        service_provider.project_service,
        service_provider.database_service,
        metadata_export_interface,
    )


@pytest.fixture()
def image_import_service(
    scheduler: Scheduler, service_provider: ServiceProvider, schema: RootSchema
):
    yield ImageImportService(
        scheduler,
        service_provider.database_service,
        list(schema.images.values()),
    )


@pytest.fixture()
def image_export_service(
    scheduler: Scheduler, service_provider: ServiceProvider, schema: RootSchema
):
    yield ImageExportService(
        scheduler,
        service_provider.database_service,
        list(schema.images.values()),
    )


@pytest.fixture()
def celery_app(
    config: ExampleConfig,
    service_provider: ServiceProvider,
    metadata_import_interface: MetadataImportInterface,
    metadata_export_interface: MetadataExportInterface,
    image_import_interface: ImageImportInterface,
    image_export_interface: ImageExportInterface,
):
    yield SlideTapTaskAppFactory.create_celery_worker_app(
        config,
        service_provider,
        metadata_import_interface=metadata_import_interface,
        metadata_export_interface=metadata_export_interface,
        image_import_interface=image_import_interface,
        image_export_interface=image_export_interface,
        name=__name__,
    )


@pytest.fixture()
def project_schema(schema: RootSchema):
    yield schema.project
