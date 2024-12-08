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
from slidetap.model.attribute import CodeAttribute
from slidetap.model.code import Code
from slidetap.model.schema.attribute_schema import ListAttributeSchema
from slidetap.services import (
    HardCodedBasicAuthTestService,
    JwtLoginService,
    MapperService,
)
from slidetap.services.validation_service import ValidationService
from slidetap.storage import Storage
from slidetap.task import Scheduler, TaskClassFactory
from slidetap.web.app_factory import SlideTapWebAppFactory
from slidetap.web.controller.login import BasicAuthLoginController
from slidetap.web.exporter import BackgroundImageExporter
from slidetap.web.importer import BackgroundImageImporter


def add_example_mappers(app: Flask, with_mappers: Optional[Sequence[str]] = None):
    with app.app_context():
        validation_service = ValidationService()
        mapper_service = MapperService(validation_service)
        schema = ExampleSchema()
        if with_mappers is None or "collection" in with_mappers:
            collection_schema = schema.samples["specimen"].attributes["collection"]
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
            fixation_schema = schema.samples["specimen"].attributes["fixation"]
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
            sampling_method_schema = schema.samples["block"].attributes[
                "block_sampling"
            ]
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
            embedding_schema = schema.samples["block"].attributes["embedding"]
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
            staining_schema = schema.samples["slide"].attributes["staining"]
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
    storage: Optional[Storage] = None,
    scheduler: Optional[Scheduler] = None,
    with_mappers: Optional[Sequence[str]] = None,
    celery_task_class_factory: Optional[TaskClassFactory] = None,
) -> Flask:
    if config is None:
        config = Config()
    if storage is None:
        storage = Storage(config.storage_path)
    if scheduler is None:
        scheduler = Scheduler()
    image_exporter = BackgroundImageExporter(scheduler, storage)
    metadata_exporter = JsonMetadataExporter(scheduler, storage)
    login_service = JwtLoginService(config)
    auth_service = HardCodedBasicAuthTestService({"test": "test"})
    login_controller = BasicAuthLoginController(auth_service, login_service)
    image_importer = BackgroundImageImporter(scheduler, "wsi")
    metadata_importer = ExampleMetadataImporter(scheduler)
    app = SlideTapWebAppFactory.create(
        auth_service,
        login_service,
        login_controller,
        image_importer,
        image_exporter,
        metadata_importer,
        metadata_exporter,
        config,
        celery_task_class_factory=celery_task_class_factory,
    )
    add_example_mappers(app, with_mappers)
    return app
