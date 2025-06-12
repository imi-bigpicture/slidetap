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
from uuid import uuid4

import pytest
from slidetap import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.apps.example.config import ExampleConfig, ExampleConfigTest
from slidetap.apps.example.interfaces.image_export import (
    ExampleImageExportInterface,
    ExampleImagePostProcessor,
)
from slidetap.apps.example.interfaces.image_import import ExampleImageImportInterface
from slidetap.apps.example.interfaces.metadata_export import (
    ExampleMetadataExportInterface,
)
from slidetap.apps.example.interfaces.metadata_import import (
    ExampleImagePreProcessor,
    ExampleMetadataImportInterface,
)
from slidetap.apps.example.mapper_injector import ExampleMapperInjector
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
from slidetap.services import (
    BatchService,
    DatabaseService,
    ProjectService,
    SchemaService,
    StorageService,
)
from slidetap.services.mapper_service import MapperService
from slidetap.services.validation_service import ValidationService
from slidetap.task import Scheduler
from slidetap.task.app_factory import SlideTapTaskAppFactory
from slidetap.web.services.image_export_service import ImageExportService
from slidetap.web.services.image_import_service import ImageImportService
from slidetap.web.services.metadata_export_service import MetadataExportService
from slidetap.web.services.metadata_import_service import MetadataImportService

# @pytest.fixture
# def app():
#     app = Flask(__name__)
#     app.config.update({"TESTING": True})
#     yield app


@pytest.fixture
def schema():
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
        attributes={},
        mapper_groups=[],
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
        display_value_format_string=None,
        attributes={"fixation": fixation_schema, "collection": collection_schema},
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
        parents=[uuid4()],
        children=[uuid4()],
        images=[],
        observations=[],
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
def scheduler():
    yield Scheduler()


@pytest.fixture()
def database_service(config: Config):
    yield DatabaseService(config.database_config)


@pytest.fixture()
def schema_service(schema: ExampleSchema):
    yield SchemaService(schema)


@pytest.fixture()
def storage_service(config: Config):
    """Fixture for the storage service."""
    yield StorageService(config.storage_config)


@pytest.fixture()
def validation_service(
    schema_service: SchemaService,
    database_service: DatabaseService,
):
    yield ValidationService(schema_service, database_service)


@pytest.fixture()
def mapper_service(
    validation_service: ValidationService,
    database_service: DatabaseService,
):
    """Fixture for the mapper service."""
    yield MapperService(validation_service, database_service)


@pytest.fixture()
def mapper_injector(
    schema: ExampleSchema,
    mapper_service: MapperService,
):
    """Fixture for the mapper injector."""
    yield ExampleMapperInjector(
        schema=schema,
        mapper_service=mapper_service,
    )


@pytest.fixture()
def image_pre_processor(storage_service: StorageService, schema_service: SchemaService):
    yield ExampleImagePreProcessor(storage_service, schema_service)


@pytest.fixture()
def image_post_processor(
    config: Config,
    storage_service: StorageService,
    schema_service: SchemaService,
):
    """Fixture for the image post-processor."""
    yield ExampleImagePostProcessor(config, storage_service, schema_service)


@pytest.fixture()
def metadata_import_interface(
    schema_service: SchemaService, image_pre_processor: ExampleImagePreProcessor
):
    yield ExampleMetadataImportInterface(schema_service, image_pre_processor)


@pytest.fixture()
def metadata_export_interface(
    database_service: DatabaseService,
    schema_service: SchemaService,
    storage_service: StorageService,
):
    yield ExampleMetadataExportInterface(
        database_service, schema_service, storage_service
    )


@pytest.fixture()
def image_import_interface(config: ExampleConfig):
    yield ExampleImageImportInterface(config)


@pytest.fixture()
def image_export_interface(image_post_processor: ExampleImagePostProcessor):
    yield ExampleImageExportInterface(image_post_processor)


@pytest.fixture()
def metadata_import_service(
    scheduler: Scheduler,
    batch_service: BatchService,
    database_service: DatabaseService,
    schema_service: SchemaService,
    metadata_import_interface: MetadataImportInterface,
):
    yield MetadataImportService(
        scheduler=scheduler,
        batch_service=batch_service,
        database_service=database_service,
        schema_service=schema_service,
        metadata_import_interface=metadata_import_interface,
    )


@pytest.fixture()
def metadata_export_service(
    scheduler: Scheduler,
    project_service: ProjectService,
    database_service: DatabaseService,
    metadata_export_interface: MetadataExportInterface,
):
    yield MetadataExportService(
        scheduler=scheduler,
        project_service=project_service,
        database_service=database_service,
        metadata_export_interface=metadata_export_interface,
    )


@pytest.fixture()
def image_import_service(
    scheduler: Scheduler,
    batch_service: BatchService,
    schema_service: SchemaService,
    database_service: DatabaseService,
    schema: RootSchema,
):
    yield ImageImportService(
        scheduler=scheduler,
        batch_service=batch_service,
        schema_service=schema_service,
        database_service=database_service,
        root_schema=schema,
    )


@pytest.fixture()
def image_export_service(
    scheduler: Scheduler,
    batch_service: BatchService,
    schema_service: SchemaService,
    database_service: DatabaseService,
    schema: RootSchema,
):
    yield ImageExportService(
        scheduler=scheduler,
        batch_service=batch_service,
        schema_service=schema_service,
        database_service=database_service,
        root_schema=schema,
    )


@pytest.fixture()
def project_schema(schema: RootSchema):
    yield schema.project
