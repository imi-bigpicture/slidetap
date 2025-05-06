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

"""Flask app factory for example application."""

from typing import Optional, Sequence
from uuid import uuid4

from flask import Flask
from slidetap.apps.example.metadata_exporter import JsonMetadataExporter
from slidetap.apps.example.metadata_importer import (
    ExampleMetadataImporter,
)
from slidetap.apps.example.schema import ExampleSchema
from slidetap.config import Config
from slidetap.external_interfaces import (
    BackgroundImageExporter,
    BackgroundImageImporter,
)
from slidetap.model import Code, CodeAttribute, ListAttributeSchema
from slidetap.service_provider import ServiceProvider
from slidetap.services import (
    DatabaseService,
    HardCodedBasicAuthTestService,
    JwtLoginService,
    MapperService,
    SchemaService,
    ValidationService,
)
from slidetap.task import Scheduler, TaskClassFactory
from slidetap.web.app_factory import SlideTapWebAppFactory
from slidetap.web.controller.login import BasicAuthLoginController


def add_example_mappers(config: Config, with_mappers: Optional[Sequence[str]] = None):
    schema = ExampleSchema()
    database_service = DatabaseService(config.database_uri)
    schema_service = SchemaService(schema)
    validation_service = ValidationService(schema_service, database_service)
    mapper_service = MapperService(validation_service, database_service)
    if with_mappers is None or "collection" in with_mappers:
        collection_schema = schema.specimen.attributes["collection"]
        collection_mapper = mapper_service.get_or_create_mapper(
            "collection",
            collection_schema.uid,
        )
        mapper_service.get_or_create_mapping(
            collection_mapper.uid,
            "Excision",
            CodeAttribute(
                uuid4(),
                collection_schema.uid,
                Code("Excision", "CUSTOM", "Excision"),
                display_value="excision",
            ),
        )
    if with_mappers is None or "fixation" in with_mappers:
        fixation_schema = schema.specimen.attributes["fixation"]
        fixation_mapper = mapper_service.get_or_create_mapper(
            "fixation", fixation_schema.uid
        )
        mapper_service.get_or_create_mapping(
            fixation_mapper.uid,
            "Neutral Buffered Formalin",
            CodeAttribute(
                uuid4(),
                fixation_schema.uid,
                Code(
                    "Neutral Buffered Formalin",
                    "CUSTOM",
                    "Neutral Buffered Formalin",
                ),
                display_value="formalin",
            ),
        )
    if with_mappers is None or "block_sampling" in with_mappers:
        sampling_method_schema = schema.block.attributes["block_sampling"]
        sampling_method_mapper = mapper_service.get_or_create_mapper(
            "sampling method", sampling_method_schema.uid
        )
        mapper_service.get_or_create_mapping(
            sampling_method_mapper.uid,
            "Dissection",
            CodeAttribute(
                uuid4(),
                sampling_method_schema.uid,
                Code("Dissection", "CUSTOM", "Dissection"),
                display_value="dissection",
            ),
        )
    if with_mappers is None or "embedding" in with_mappers:
        embedding_schema = schema.block.attributes["embedding"]
        embedding_mapper = mapper_service.get_or_create_mapper(
            "embedding", embedding_schema.uid
        )
        mapper_service.get_or_create_mapping(
            embedding_mapper.uid,
            "Paraffin wax",
            CodeAttribute(
                uuid4(),
                embedding_schema.uid,
                Code("Paraffin wax", "CUSTOM", "Paraffin wax"),
                display_value="paraffin",
            ),
        )
    if with_mappers is None or "staining" in with_mappers:
        staining_schema = schema.slide.attributes["staining"]
        assert isinstance(staining_schema, ListAttributeSchema)
        stain_mapper = mapper_service.get_or_create_mapper(
            "stain", staining_schema.attribute.uid, staining_schema.uid
        )
        mapper_service.get_or_create_mapping(
            stain_mapper.uid,
            "hematoxylin",
            CodeAttribute(
                uuid4(),
                staining_schema.attribute.uid,
                Code("hematoxylin", "CUSTOM", "hematoxylin"),
                display_value="hematoxylin",
            ),
        )
        mapper_service.get_or_create_mapping(
            stain_mapper.uid,
            "water soluble eosin",
            CodeAttribute(
                uuid4(),
                staining_schema.attribute.uid,
                Code("water soluble eosin", "CUSTOM", "water soluble eosin"),
                display_value="eosin",
            ),
        )


def create_app(
    config: Optional[Config] = None,
    scheduler: Optional[Scheduler] = None,
    with_mappers: Optional[Sequence[str]] = None,
    celery_task_class_factory: Optional[TaskClassFactory] = None,
) -> Flask:
    schema = ExampleSchema()
    if config is None:
        config = Config()
    if scheduler is None:
        scheduler = Scheduler()
    service_provider = ServiceProvider(config, schema)
    image_exporter = BackgroundImageExporter(
        scheduler, service_provider.database_service, [schema.image]
    )
    metadata_exporter = JsonMetadataExporter(
        scheduler, service_provider.project_service
    )
    login_service = JwtLoginService(config)
    auth_service = HardCodedBasicAuthTestService({"test": "test"})
    login_controller = BasicAuthLoginController(auth_service, login_service)
    image_importer = BackgroundImageImporter(
        scheduler, service_provider.database_service, [schema.image]
    )
    metadata_importer = ExampleMetadataImporter(
        scheduler, service_provider.schema_service
    )
    app = SlideTapWebAppFactory.create(
        auth_service,
        login_service,
        login_controller,
        image_importer,
        image_exporter,
        metadata_importer,
        metadata_exporter,
        service_provider,
        config,
        celery_task_class_factory=celery_task_class_factory,
    )
    add_example_mappers(config, with_mappers)
    return app
