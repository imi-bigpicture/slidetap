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

"""FastAPI app factory for example application."""

import logging
from typing import List, Optional, Sequence
from uuid import uuid4

from celery import Celery
from fastapi import FastAPI
from slidetap.apps.example.config import ExampleConfig
from slidetap.apps.example.interfaces import (
    ExampleMetadataExportInterface,
    ExampleMetadataImportInterface,
)
from slidetap.apps.example.schema import ExampleSchema
from slidetap.config import Config
from slidetap.model import Code, CodeAttribute, ListAttributeSchema, Mapper
from slidetap.service_provider import ServiceProvider
from slidetap.services import (
    DatabaseService,
    MapperService,
    SchemaService,
    ValidationService,
)
from slidetap.web.app_factory import SlideTapAppFactory
from slidetap.web.routers.login_router import LoginRouter
from slidetap.web.services import (
    HardCodedBasicAuthTestService,
)


def add_example_mappers(config: Config, with_mappers: Optional[Sequence[str]] = None):
    schema = ExampleSchema()
    database_service = DatabaseService(config.database_uri)
    schema_service = SchemaService(schema)
    validation_service = ValidationService(schema_service, database_service)
    mapper_service = MapperService(validation_service, database_service)
    mappers: List[Mapper] = []
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
                uid=uuid4(),
                schema_uid=collection_schema.uid,
                original_value=Code(
                    code="Excision", scheme="CUSTOM", meaning="Excision"
                ),
                display_value="excision",
            ),
        )
        mappers.append(collection_mapper)
    if with_mappers is None or "fixation" in with_mappers:
        fixation_schema = schema.specimen.attributes["fixation"]
        fixation_mapper = mapper_service.get_or_create_mapper(
            "fixation", fixation_schema.uid
        )
        mapper_service.get_or_create_mapping(
            fixation_mapper.uid,
            "Neutral Buffered Formalin",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=fixation_schema.uid,
                original_value=Code(
                    code="Neutral Buffered Formalin",
                    scheme="CUSTOM",
                    meaning="Neutral Buffered Formalin",
                ),
                display_value="formalin",
            ),
        )
        mappers.append(fixation_mapper)
    if with_mappers is None or "block_sampling" in with_mappers:
        sampling_method_schema = schema.block.attributes["block_sampling"]
        sampling_method_mapper = mapper_service.get_or_create_mapper(
            "sampling method", sampling_method_schema.uid
        )
        mapper_service.get_or_create_mapping(
            sampling_method_mapper.uid,
            "Dissection",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=sampling_method_schema.uid,
                original_value=Code(
                    code="Dissection", scheme="CUSTOM", meaning="Dissection"
                ),
                display_value="dissection",
            ),
        )
        mappers.append(sampling_method_mapper)
    if with_mappers is None or "embedding" in with_mappers:
        embedding_schema = schema.block.attributes["embedding"]
        embedding_mapper = mapper_service.get_or_create_mapper(
            "embedding", embedding_schema.uid
        )
        mapper_service.get_or_create_mapping(
            embedding_mapper.uid,
            "Paraffin wax",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=embedding_schema.uid,
                original_value=Code(
                    code="Paraffin wax", scheme="CUSTOM", meaning="Paraffin wax"
                ),
                display_value="paraffin",
            ),
        )
        mappers.append(embedding_mapper)
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
                uid=uuid4(),
                schema_uid=staining_schema.attribute.uid,
                original_value=Code(
                    code="hematoxylin", scheme="CUSTOM", meaning="hematoxylin"
                ),
                display_value="hematoxylin",
            ),
        )
        mapper_service.get_or_create_mapping(
            stain_mapper.uid,
            "water soluble eosin",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=staining_schema.attribute.uid,
                original_value=Code(
                    code="water soluble eosin",
                    scheme="CUSTOM",
                    meaning="water soluble eosin",
                ),
                display_value="eosin",
            ),
        )
        mappers.append(stain_mapper)
    mapper_group = mapper_service.get_or_create_mapper_group(
        "Example mappers",
        default_enabled=True,
    )
    logging.info(
        f"Adding mappers {[mapper.name for mapper in mappers]} to group {mapper_group.name} with uid {mapper_group.uid}"
    )
    mapper_group = mapper_service.add_mappers_to_group(mapper_group, mappers)
    logging.info(
        f"Mappers in group {mapper_group.name}: {[mapper for mapper in mapper_group.mappers]}, default enabled: {mapper_group.default_enabled}"
    )


def create_app(
    config: Optional[ExampleConfig] = None,
    with_mappers: Optional[Sequence[str]] = None,
    celery_app: Optional[Celery] = None,
) -> FastAPI:
    schema = ExampleSchema()
    if config is None:
        config = ExampleConfig()

    service_provider = ServiceProvider(config, schema)

    metadata_import_interface = ExampleMetadataImportInterface(service_provider)
    metadata_export_interface = ExampleMetadataExportInterface(service_provider)

    auth_service = HardCodedBasicAuthTestService({"test": "test"})
    login_router = LoginRouter(auth_service)

    app = SlideTapAppFactory.create(
        auth_service=auth_service,
        login_router=login_router,
        metadata_import_interface=metadata_import_interface,
        metadata_export_interface=metadata_export_interface,
        service_provider=service_provider,
        config=config,
        celery_app=celery_app,
    )
    add_example_mappers(config, with_mappers)
    return app
